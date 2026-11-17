import sys
import traceback
import train_unet

print("=== STARTING TRAIN MODEL ===", flush=True)
try:
    res = train_unet.train_model()
    print("=== SUCCESS ===", flush=True)
    print(res, flush=True)
except Exception as e:
    print("=== EXCEPTION OCCURRED ===", flush=True)
    traceback.print_exc()
    sys.exit(1)
