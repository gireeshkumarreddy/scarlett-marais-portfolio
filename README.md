# Scarlett Marais — marketing portfolio

A red, editorial portfolio site for a marketing and brand strategist, plus a 40-second launch film recorded from the live site.

- `index.html` — the whole site (HTML, CSS and JS in one file). GSAP, ScrollTrigger, Flip, Draggable and Lenis load from jsDelivr.
- `script-words.js` — pre-shaped outlines of the hand-lettered words (Imperial Script, OFL) used for the writing animation.
- `video/scarlett-marais-launch.mp4` — the launch film, 1920×1080 at 60 fps.
- `showcase/` — the film's stage page (`stage.html`), a virtual clock (`vclock.js`) and the frame-by-frame recorder (`record.py`).
- `tools/make-script-words.py` — regenerates `script-words.js` when you change a hand-lettered word.

## View the site

Serve the folder and open it in a browser (it needs an internet connection for fonts, libraries and photos):

```bash
python -m http.server 5517
```

Then open http://localhost:5517.

## Re-render the film

Needs Google Chrome, ffmpeg and `pip install playwright`.

```bash
python showcase/record.py
```

Add `--stills 10,25` to render only a few frames for checking.

## Credits

Photography from [Unsplash](https://unsplash.com). The name, copy, numbers and testimonials are placeholder content.
