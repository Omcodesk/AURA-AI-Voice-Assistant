import sounddevice as sd
print("ALL INPUT DEVICES:")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(f"  [{i}] {d['name']} ({d['max_input_channels']}ch, {int(d['default_samplerate'])}Hz)")
print()
default = sd.query_devices(kind="input")
print(f"Current default: {default['name']}")
print(f"Default index:   {default['index']}")
