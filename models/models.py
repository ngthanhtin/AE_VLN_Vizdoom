import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from language_model.language_model import tfidf_loading, WordEmbedding, SentenceEmbedding
from attention.convolve_attention.attention import ConvolvedAttention
from attention.convolve_attention.cf_attention import CF_ConvolvedAttention
from attention.dual_attention.attention import DualAttention
import cv2

def normalized_columns_initializer(weights, std=1.0):
    out = torch.randn(weights.size())
    out *= std / torch.sqrt(out.pow(2).sum(1, keepdim=True).expand_as(out))
    return out


def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        weight_shape = list(m.weight.data.size())
        fan_in = np.prod(weight_shape[1:4])
        fan_out = np.prod(weight_shape[2:4]) * weight_shape[0]
        w_bound = np.sqrt(6. / (fan_in + fan_out))
        m.weight.data.uniform_(-w_bound, w_bound)
        m.bias.data.fill_(0)
    elif classname.find('Linear') != -1:
        weight_shape = list(m.weight.data.size())
        fan_in = weight_shape[1]
        fan_out = weight_shape[0]
        w_bound = np.sqrt(6. / (fan_in + fan_out))
        m.weight.data.uniform_(-w_bound, w_bound)
        # if m.bias is not None:
        #     m.bias.data.fill_(0)

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

def figure_to_array(fig):
    fig.canvas.draw()
    return np.array(fig.canvas.renderer._renderer)

#Show attention
def plot_attention(imgs, original_img, text):
    original_img = original_img[0].detach().cpu().numpy().transpose((1, 2, 0))
    fig = plt.figure()
    
    imgs = imgs.detach().cpu().numpy().transpose((0, 2, 3, 1))
    # imgs = imgs.sum(0)
    # imgs = imgs.detach().cpu().numpy().transpose((1, 2, 0))
    # img = imgs/255.0
    # img = cv2.resize(img, (300, 168))
    
    # plt.imshow(img, cmap='jet', alpha=0.5)
    # plt.tight_layout()
    # plt.show()
    combined_imgs = imgs[0]+imgs[1]+imgs[2]+imgs[3]+imgs[4]
    combined_imgs = combined_imgs/255.
    combined_imgs = cv2.resize(combined_imgs, (300, 168))
    for i in range(5):
        img = imgs[i]/255.0
        img = cv2.resize(img, (300, 168))
        plt.imshow(original_img, cmap='gray')
        plt.imshow(combined_imgs, cmap='jet', alpha=0.5)
        if i == 0:
            no_text = '1st'
        if i == 1:
            no_text = '2nd'
        if i == 2:
            no_text = '3rd'
        if i == 3:
            no_text = '4th'
        if i == 4:
            no_text = '5th'
        # plt.text(120, 200, '{} attention map'.format(no_text), fontsize = 11)
        plt.tight_layout()
        # plt.show()
        if i == 0:
            saved_image = figure_to_array(fig)
            saved_image = cv2.cvtColor(saved_image, cv2.COLOR_RGB2BGR)
            # saved_image = np.frombuffer(canvas.tostring_rgb(), dtype='uint8')
            return saved_image

class A3C_LSTM_GA(torch.nn.Module):

    def __init__(self, args, ae_model=None):
        super(A3C_LSTM_GA, self).__init__()
        self.args = args
        self.prelu = nn.PReLU() 
        #init auto encoder
        if args.auto_encoder:
            self.ae_model = ae_model
            self.convert = nn.Linear(50400, 8704)
        else:
            # Image Processing
            self.conv1 = nn.Conv2d(3, 128, kernel_size=8, stride=4) 
            self.conv2 = nn.Conv2d(128, 64, kernel_size=4, stride=2)
            self.conv3 = nn.Conv2d(64, 64, kernel_size=4, stride=2)

        #language model
        self.w_emb = WordEmbedding(args.vocab_size, 32, 0.0) # , op='c'
        # self.w_emb = tfidf_loading(self.w_emb, args.dictionary)
        self.s_emb = SentenceEmbedding(32, 256, 1, False, 0.0, 'GRU')
        
        #attention
        if args.attention == 'convolve':
            self.v_att = ConvolvedAttention(5, 8*17, 256, 64) # 5 ,1,8,17
            self.conv_4 = nn.Conv2d(1, 64, kernel_size=3, stride=2)
            self.conv_5 = nn.Conv2d(64, 64, kernel_size=3, stride=2)
        if args.attention == 'cf_convolve':
            self.v_att = CF_ConvolvedAttention(5, 8*17, 256, 32, 64) # 5 ,1,8,17
            self.conv_4 = nn.Conv2d(1, 64, kernel_size=3, stride=2)
            self.conv_5 = nn.Conv2d(64, 64, kernel_size=3, stride=2)
        if args.attention == 'gated':
            self.attn_linear = nn.Linear(256, 64)

        # Time embedding layer, helps in stabilizing value prediction
        self.time_emb_dim = 32
        self.time_emb_layer = nn.Embedding(
                args.max_episode_length+1,
                self.time_emb_dim)

        # A3C-LSTM layers
        if args.attention == 'convolve':
            self.linear = nn.Linear(960, 256)
        if args.attention == 'cf_convolve':
            self.linear = nn.Linear(960, 256)
        if args.attention == 'gated':
            self.linear = nn.Linear(64*8*17, 256)

        self.lstm = nn.LSTMCell(256, 256)
        self.critic_linear = nn.Linear(256 + self.time_emb_dim, 1)
        self.actor_linear = nn.Linear(256 + self.time_emb_dim, 3)

        # Initializing weights
        # self.apply(weights_init)
        self.actor_linear.weight.data = normalized_columns_initializer(
            self.actor_linear.weight.data, 0.01)
        self.actor_linear.bias.data.fill_(0)
        self.critic_linear.weight.data = normalized_columns_initializer(
            self.critic_linear.weight.data, 1.0)
        self.critic_linear.bias.data.fill_(0)

        self.lstm.bias_ih.data.fill_(0)
        self.lstm.bias_hh.data.fill_(0)

        self.train()


    def forward(self, inputs):
        
        if self.args.auto_encoder:
            ae_input, x, input_inst, (tx, hx, cx) = inputs
            if self.args.attention == "cf_convolve":
                encoder, (x1,x2,x3) = self.ae_model.forward_pass(ae_input, return_conv=True)
            else:
                encoder = self.ae_model.forward_pass(ae_input)
            decoder = self.ae_model.reconstruct_pass(encoder)
            x_emb = encoder
        else:
            x, input_inst, (tx, hx, cx) = inputs
            # Get the image representation
            if self.args.attention == "gated":
                x1 = F.relu(self.conv1(x))
                x2 = F.relu(self.conv2(x1))
                x_image_rep = F.relu(self.conv3(x2))    
            else:
                x1 = self.prelu(self.conv1(x))
                x2 = self.prelu(self.conv2(x1))
                x_image_rep = self.prelu(self.conv3(x2))
            x_emb = x_image_rep

        tx = tx.long()
        
        w_emb = self.w_emb(input_inst.long())
        s_emb = self.s_emb(w_emb)
        
        if self.args.attention == "convolve":
            att = self.v_att(x_emb, s_emb)
            att = self.conv_4(att)
            att = self.prelu(att)
            att = self.conv_5(att)
            att = self.prelu(att)
            att = att.view(-1).unsqueeze(0)
        if self.args.attention == "cf_convolve":
            att = self.v_att([x1,x2,x_emb], s_emb) # , w_emb, input_inst
            att_img = plot_attention(att, x, input_inst)
            att = self.conv_4(att)
            att = self.prelu(att)
            att = self.conv_5(att)
            att = self.prelu(att)
            att = att.view(-1).unsqueeze(0)
        if self.args.attention == "gated":
            x_attention = F.sigmoid(self.attn_linear(s_emb))
            x_attention = x_attention.unsqueeze(2).unsqueeze(3)
            x_attention = x_attention.expand(1, 64, 8, 17)
            x = x_emb*x_attention
            att = x.view(x.size(0), -1)
        
        x = att
        
        # A3C-LSTM
        if self.args.attention == "gated":
            x = F.relu(self.linear(x))
        else:
            x = self.prelu(self.linear(x))

        hx, cx = self.lstm(x, (hx, cx))
        time_emb = self.time_emb_layer(tx)
        x = torch.cat((hx, time_emb.view(-1, self.time_emb_dim)), 1)

        if self.args.auto_encoder:
            return self.critic_linear(x), self.actor_linear(x), (hx, cx), decoder
        return self.critic_linear(x), self.actor_linear(x), (hx, cx), att_img

    