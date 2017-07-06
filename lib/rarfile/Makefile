
prefix = /usr/local

all:
	pyflakes3 rarfile.py
	tox

install:
	python setup.py install --prefix=$(prefix)

tgz: clean
	python setup.py sdist

clean:
	rm -rf __pycache__ build dist
	rm -f *.pyc MANIFEST *.orig *.rej *.html *.class
	rm -rf doc/_build doc/_static doc/_templates doc/html
	rm -rf .coverage cover*
	rm -rf *.egg-info
	rm -f test/files/*.rar.[pjt]* *.diffs

toxclean: clean
	rm -rf .tox

rbuild:
	curl -X POST https://readthedocs.org/build/6715

upload:
	python setup.py sdist upload

ack:
	for fn in test/files/*.py27; do \
		cp $$fn `echo $$fn | sed 's/py27/exp/'` || exit 1; \
	done

