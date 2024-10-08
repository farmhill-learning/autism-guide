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
