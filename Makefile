clean:
	find . -type f -name '*.py[c0]' -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name '.DS_Store' -delete

clean-all: clean dist-clean env-clean

dist: clean dist-clean
	python3 setup.py sdist

dist-clean:
	rm -rf build dist *.egg-info

install:
	python setup.py install

run: env
	env/bin/python taiga_events/cli.py

test:
	TESTING=True env/bin/python setup.py test

env: env-clean
	virtualenv -p python3 env 
	env/bin/pip install nose
	env/bin/pip install -e .

env-clean:
	rm -rf env

env-install: env
	env/bin/python setup.py install

env-run:
	env/bin/taiga-events

