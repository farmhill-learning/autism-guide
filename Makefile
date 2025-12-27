
default: build

build:
	python src/website.py

serve:
	python -m http.server
