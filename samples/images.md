# Document with images

This sample shows how images referenced from Markdown end up embedded in the
Word document when you upload a ZIP.

## Inline image

![Red box](images/pixel.png)

## Referenced image

The images live as real files inside the ZIP:

```
document.md
images/
  └── pixel.png
```

zip this folder, then upload the `.zip`. The images are embedded into the
`.docx`.