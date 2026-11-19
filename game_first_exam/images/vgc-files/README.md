# VGC adapter files

Files-only image for the thin native VGC adapter and its validation. Built from
`game_first_exam/benchmarks/vgc` with `scripts/files_image.py build vgc-files`,
then pinned with `scripts/files_image.py pin vgc-files <digest>`. No upstream
engine (poke-env / Pokemon Showdown) is modified; the engine is installed inside
the sim container, not carried in this image.
