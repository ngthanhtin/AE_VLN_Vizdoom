# Auto Encoder Vision Language Navigation in Vizdoom
## Using Stacked Attention and Auto-Encoder for Task-Oriented Language Grounding

[Using Stacked Attention and Auto-Encoder for Task-Oriented Language Grounding](None)<br />
Nguyen T.Tin, Che Peng Lim, Kim Yong Guk<br />
Sejong University, Seoul, Korea <br/>
Deakin University, Australia

![example](./docs/example.gif)

### This repository contains:
- Code for training an A3C-LSTM agent using Stacked Attention and Auto-Encoder
- Code for Doom-based language grounding environment

## Dependencies
- [ViZDoom](https://github.com/mwydmuch/ViZDoom)
- [PyTorch](http://pytorch.org)
- Opencva

## Usage

### Using the Environment
For running a random agent:
```
python env_test.py
```
To play in the environment:
```
python env_test.py --interactive 1
```
To change the difficulty of the environment (easy/medium/hard):
```
python env_test.py -d easy
```

### Training
Example training a Stacked Attention A3C-LSTM agent with 4 threads:
```
python a3c_main.py --num-processes 4 --evaluate 0 (1) --difficulty easy (medium, hard) --attention san (dual, gated, convolve)
```


Example training a Stacked Attention and Auto-Encoder A3C-LSTM with  agent with 4 threads:
```
python a3c_main.py --num-processes 4 --evaluate 0 (1) --difficulty easy (medium, hard) --auto-encoder --attention san (dual, gated, convolve)
```

The code will save the best model at `./saved/`.
### Testing
To the test the pre-trained model for Multitask Generalization:
```
python a3c_main.py --evaluate 1 --load saved/pretrained_model
```
To the test the pre-trained model for Zero-shot Task Generalization:
```
python a3c_main.py --evaluate 2 --load saved/pretrained_model
``` 
To the visualize the model while testing add '--visualize 1':<br />
```
python a3c_main.py --evaluate 2 --load saved/pretrained_model --visualize 1
``` 
To test the trained model, use `--load saved/model_best` in the above commands.
```

## Cite as
>Nguyen T.Tin, Che Peng Lim, Kim Yong Guk, 2022. Using Stacked Attention and Auto-Encoder for Task-Oriented Language Grounding. arXiv preprint arXiv:1706.07230. ([PDF](None))

### Bibtex:
```
@article{zzzzzzzzzzzzzz,
  title={Using Stacked Attention and Auto-Encoder for Task-Oriented Language Grounding},
  author={Nguyen T.Tin, Che Peng Lim, Kim Yong Guk},
  journal={arXiv preprint arXiv:1706.07230},
  year={2022}
}
```

## Acknowledgements
This repository uses ViZDoom API (https://github.com/mwydmuch/ViZDoom) and parts of the code from the API. This is a PyTorch implementation based on [this repo](https://github.com/devendrachaplot/DeepRL-Grounding).
