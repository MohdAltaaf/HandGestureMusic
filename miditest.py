import mido, time

names = mido.get_output_names()
print(names)

out = mido.open_output(names[0])
out.send(mido.Message('note_on', note=60, velocity=100))
time.sleep(1)
out.send(mido.Message('note_off', note=60))