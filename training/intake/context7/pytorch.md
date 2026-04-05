# PyTorch

PyTorch is an open-source machine learning framework that provides tensor computation with GPU acceleration and a dynamic computational graph for building and training neural networks. It uses a tape-based autograd system for automatic differentiation.

## Autograd

PyTorch's autograd engine automatically computes gradients by recording operations on tensors:

```python
import torch

# Create tensors with gradient tracking
x = torch.tensor([2.0, 3.0], requires_grad=True)
y = torch.tensor([4.0, 5.0], requires_grad=True)

# Forward pass: compute output
z = x * y + x ** 2
loss = z.sum()

# Backward pass: compute gradients
loss.backward()

# dz/dx = y + 2*x
print(x.grad)  # tensor([8., 11.])
# dz/dy = x
print(y.grad)  # tensor([2., 3.])

# Disable gradient tracking for inference
with torch.no_grad():
    output = x * y
    print(output.requires_grad)  # False

# Detach from computation graph
z_detached = z.detach()

# Custom autograd function
class MyReLU(torch.autograd.Function):
    @staticmethod
    def forward(ctx, input):
        ctx.save_for_backward(input)
        return input.clamp(min=0)

    @staticmethod
    def backward(ctx, grad_output):
        input, = ctx.saved_tensors
        grad_input = grad_output.clone()
        grad_input[input < 0] = 0
        return grad_input

relu = MyReLU.apply
output = relu(torch.tensor([-1.0, 0.5, 2.0], requires_grad=True))
```

## Neural Network Modules

Build neural networks using `nn.Module` as the base class:

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

# Define a neural network
class SimpleNet(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        x = F.relu(self.bn1(self.fc1(x)))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

model = SimpleNet(784, 256, 10)
print(model)

# Count parameters
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Total: {total_params}, Trainable: {trainable_params}")

# Move model to device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

# Sequential model
model_seq = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Linear(128, 10),
)

# Save and load model
torch.save(model.state_dict(), "model.pth")
model.load_state_dict(torch.load("model.pth"))
```

## apply() for Custom Initialization

Use `apply()` to recursively initialize weights across all modules:

```python
import torch
import torch.nn as nn

class ConvNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.fc1 = nn.Linear(64 * 8 * 8, 256)
        self.fc2 = nn.Linear(256, 10)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.max_pool2d(x, 2)
        x = torch.relu(self.conv2(x))
        x = torch.max_pool2d(x, 2)
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

# Custom initialization function
def init_weights(m):
    if isinstance(m, nn.Conv2d):
        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        if m.bias is not None:
            nn.init.constant_(m.bias, 0)
    elif isinstance(m, nn.Linear):
        nn.init.xavier_uniform_(m.weight)
        nn.init.constant_(m.bias, 0)
    elif isinstance(m, nn.BatchNorm2d):
        nn.init.constant_(m.weight, 1)
        nn.init.constant_(m.bias, 0)

model = ConvNet()
model.apply(init_weights)

# Verify initialization
for name, param in model.named_parameters():
    if 'weight' in name:
        print(f"{name}: mean={param.data.mean():.4f}, std={param.data.std():.4f}")
```

## SGD Training Loop

A complete training loop with SGD optimizer, loss tracking, and evaluation:

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Create synthetic data
X_train = torch.randn(1000, 784)
y_train = torch.randint(0, 10, (1000,))
X_test = torch.randn(200, 784)
y_test = torch.randint(0, 10, (200,))

train_dataset = TensorDataset(X_train, y_train)
test_dataset = TensorDataset(X_test, y_test)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=64)

# Model, loss, optimizer
model = SimpleNet(784, 256, 10)
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9, weight_decay=1e-4)

# Learning rate scheduler
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

# Training loop
num_epochs = 20
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, labels in train_loader:
        # Zero gradients
        optimizer.zero_grad()

        # Forward pass
        outputs = model(inputs)
        loss = criterion(outputs, labels)

        # Backward pass
        loss.backward()

        # Gradient clipping (optional)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        # Update weights
        optimizer.step()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

    scheduler.step()

    # Evaluation
    model.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for inputs, labels in test_loader:
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            test_total += labels.size(0)
            test_correct += predicted.eq(labels).sum().item()

    train_acc = 100.0 * correct / total
    test_acc = 100.0 * test_correct / test_total
    print(f"Epoch {epoch+1}/{num_epochs} | Loss: {running_loss/len(train_loader):.4f} | "
          f"Train Acc: {train_acc:.2f}% | Test Acc: {test_acc:.2f}%")
```

## torch.optim Overview

PyTorch provides several optimization algorithms:

```python
import torch.optim as optim

model = SimpleNet(784, 256, 10)

# Stochastic Gradient Descent with momentum
optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9, weight_decay=1e-4)

# Adam optimizer
optimizer = optim.Adam(model.parameters(), lr=1e-3, betas=(0.9, 0.999), weight_decay=1e-4)

# AdamW (decoupled weight decay)
optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)

# Per-parameter options (different lr for different layers)
optimizer = optim.Adam([
    {"params": model.fc1.parameters(), "lr": 1e-4},
    {"params": model.fc2.parameters(), "lr": 1e-3},
    {"params": model.fc3.parameters(), "lr": 1e-3},
], weight_decay=1e-4)

# Learning rate schedulers
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=5)
scheduler = optim.lr_scheduler.OneCycleLR(optimizer, max_lr=0.01, total_steps=1000)

# Get current learning rate
for param_group in optimizer.param_groups:
    print(f"LR: {param_group['lr']}")
```
