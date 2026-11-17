import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Check PyTorch availability dynamically
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    F = None


if TORCH_AVAILABLE:
    class DoubleConv(nn.Module):
        """(Convolution => [BN] => ReLU) * 2"""
        def __init__(self, in_channels: int, out_channels: int, mid_channels: Optional[int] = None):
            super().__init__()
            if not mid_channels:
                mid_channels = out_channels
            self.double_conv = nn.Sequential(
                nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(mid_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            )

        def forward(self, x):
            return self.double_conv(x)

    class Down(nn.Module):
        """Downscaling with maxpool then double conv"""
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.maxpool_conv = nn.Sequential(
                nn.MaxPool2d(2),
                DoubleConv(in_channels, out_channels)
            )

        def forward(self, x):
            return self.maxpool_conv(x)

    class Up(nn.Module):
        """Upscaling then double conv"""
        def __init__(self, in_channels: int, out_channels: int, bilinear: bool = True):
            super().__init__()
            if bilinear:
                self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
                self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
            else:
                self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
                self.conv = DoubleConv(in_channels, out_channels)

        def forward(self, x1, x2):
            x1 = self.up(x1)
            diffY = x2.size()[2] - x1.size()[2]
            diffX = x2.size()[3] - x1.size()[3]
            x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
            x = torch.cat([x2, x1], dim=1)
            return self.conv(x)

    class OutConv(nn.Module):
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

        def forward(self, x):
            return self.conv(x)

    class UNet(nn.Module):
        """
        PyTorch U-Net Architecture for SAR Semantic Oil-Spill Segmentation.
        Inputs: Single-band preprocessed SAR GeoTIFF intensity/dB tensor (Batch, 1, H, W).
        Classes: 0 = Background/Ocean, 1 = Oil Spill.
        """
        def __init__(self, in_channels: int = 1, num_classes: int = 1, base_c: int = 16, bilinear: bool = True):
            super().__init__()
            self.in_channels = in_channels
            self.num_classes = num_classes
            self.bilinear = bilinear
            self.base_c = base_c

            self.inc = DoubleConv(in_channels, base_c)
            self.down1 = Down(base_c, base_c * 2)
            self.down2 = Down(base_c * 2, base_c * 4)
            self.down3 = Down(base_c * 4, base_c * 8)
            factor = 2 if bilinear else 1
            self.down4 = Down(base_c * 8, (base_c * 16) // factor)
            self.up1 = Up(base_c * 16, (base_c * 8) // factor, bilinear)
            self.up2 = Up(base_c * 8, (base_c * 4) // factor, bilinear)
            self.up3 = Up(base_c * 4, (base_c * 2) // factor, bilinear)
            self.up4 = Up(base_c * 2, base_c, bilinear)
            self.outc = OutConv(base_c, num_classes)

        def forward(self, x):
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)
            x5 = self.down4(x4)
            x = self.up1(x5, x4)
            x = self.up2(x, x3)
            x = self.up3(x, x2)
            x = self.up4(x, x1)
            logits = self.outc(x)
            return logits

    class DiceLoss(nn.Module):
        """Binary & Multi-class Dice Loss for SAR oil spill segmentation"""
        def __init__(self, smooth: float = 1e-5):
            super().__init__()
            self.smooth = smooth

        def forward(self, logits, targets):
            if logits.size(1) == 1:
                probs = torch.sigmoid(logits).squeeze(1)
                targets = targets.float()
                intersection = torch.sum(probs * targets)
                cardinality = torch.sum(probs + targets)
                dice = (2.0 * intersection + self.smooth) / (cardinality + self.smooth)
                return 1.0 - dice
            else:
                probs = F.softmax(logits, dim=1)
                num_classes = logits.size(1)
                total_loss = 0.0

                for c in range(num_classes):
                    pred_c = probs[:, c, ...]
                    target_c = (targets == c).float()
                    intersection = torch.sum(pred_c * target_c)
                    cardinality = torch.sum(pred_c + target_c)
                    dice = (2.0 * intersection + self.smooth) / (cardinality + self.smooth)
                    total_loss += (1.0 - dice)

                return total_loss / num_classes

else:
    # Fallback structure if PyTorch is absent
    class UNet:
        def __init__(self, in_channels: int = 1, num_classes: int = 1):
            self.in_channels = in_channels
            self.num_classes = num_classes
