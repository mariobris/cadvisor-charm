python_scripts = lib/charms/promreg.py

lint:
	@echo "Checking Python syntax..."
	@flake8 --max-complexity=10 $(python_scripts) && echo OK

test:
	nosetests3 -w lib -v --with-cov --cov lib/charms

