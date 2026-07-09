img_path = batch / "test.png"
_make_png(str(img_path))

node = LoadAndProcessImageBatch()

images, fname, status = node.process_next(str(batch), str(processed), str(bypass),
                                           mode="single_file", index=0, seed=0, label="", dry_run=True)

assert (batch / "test.png").exists()
assert fname == "test.png"
assert status == "processed"
assert images is not None
