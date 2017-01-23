all: serve

serve:
	python dev-server.py configs/config.dev.yaml

check:
	pyflakes src
