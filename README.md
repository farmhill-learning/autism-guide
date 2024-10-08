# Autism Guide

Autism Guide from the Farmhill Learning Community.

## Comments

Comments are enabled by self-hosted instance of Isso.

### Enabling comments

To enable comments on an article, please add the following at the beginning of the `qmd` file.

```
---
format:
  html:
    include-after-body:
       - "_includes/load-comments.html"
---
```

Only the articles that have this dire will have comments enabled.

### Moderating comments

To moderate comments, please login to:
<https://comments.farmhill.in/admin/>

## Tools

The resository has a script to resize images.

To use the tools, make sure you have all the dependencies installed. You can do that by running the following command:

```
python -m pip install -r requirements.txt
```

To resize an image:

```
python tools/resize-image.py --width 200 --height 200 --output images/goodhands.jpg original-images/goodhands.jpg
Original image path: images/mat_goodhands.jpg
Image size: (1280, 960)
File size: 108 KB
---
Saved the resized image to a.jpg
Image size: (400, 300)
File size: 19 KB
```