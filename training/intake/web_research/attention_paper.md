# Attention Is All You Need

Authors: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin (2017). The paper that introduced the Transformer architecture, fundamentally changing natural language processing and machine learning.

## Abstract

The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. The Transformer is a new simple network architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. The model achieves superior quality while being more parallelizable and requiring significantly less time to train.

## Architecture

The Transformer follows an encoder-decoder structure. The encoder maps an input sequence of symbol representations to a sequence of continuous representations. The decoder then generates an output sequence one element at a time, auto-regressively consuming previously generated symbols as additional input.

### Multi-Head Attention

The core mechanism of the Transformer. Instead of performing a single attention function, the model linearly projects queries, keys, and values h times with different learned projections, performs attention in parallel, and concatenates the results. Attention(Q, K, V) = softmax(QK^T / √d_k)V. Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions.

### Scaled Dot-Product Attention

Computes the dot products of the query with all keys, divides each by √d_k (the square root of the key dimension), and applies softmax to obtain weights on the values. The scaling factor prevents the dot products from growing large in magnitude, which would push the softmax into regions with extremely small gradients.

### Positional Encoding

Since the model contains no recurrence and no convolution, positional encodings are added to the input embeddings to inject information about the relative or absolute position of tokens. Uses sine and cosine functions of different frequencies: PE(pos,2i) = sin(pos/10000^(2i/d_model)), PE(pos,2i+1) = cos(pos/10000^(2i/d_model)). Each dimension of the positional encoding corresponds to a sinusoid of different wavelength.

### Feed-Forward Networks

Each layer contains a fully connected feed-forward network applied to each position separately and identically. FFN(x) = max(0, xW₁ + b₁)W₂ + b₂. The dimensionality of inner layer is typically 4x the model dimension (d_ff = 2048 for d_model = 512).

### Layer Normalization and Residual Connections

Each sub-layer has a residual connection followed by layer normalization: LayerNorm(x + Sublayer(x)). This enables training of deep networks by allowing gradients to flow directly through the architecture.

## Results

English-to-German translation: 28.4 BLEU, surpassing previous best by over 2 BLEU. English-to-French translation: 41.8 BLEU single-model state-of-the-art. Training time: 3.5 days on eight GPUs. The architecture generalizes well to other tasks including English constituency parsing.

## Impact

The Transformer architecture became the foundation for BERT, GPT, T5, and virtually all modern large language models. Its attention mechanism enables processing of long-range dependencies efficiently, and its parallelizable nature allows scaling to billions of parameters.
