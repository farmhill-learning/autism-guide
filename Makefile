
default: build

build:
	python src/website.py

serve: build
	cd _site && python -m http.server
