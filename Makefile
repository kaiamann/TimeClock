build: cli.py timeclock.py storage.py utils.py
	pyinstaller --collect-all pyfiglet --onefile cli.py --paths .

install: dist/cli
	chmod +x dist/cli
	sudo cp dist/cli /usr/bin/timeClock

removeBinary:
	sudo rm -f /usr/bin/timeClock

removeConfig:
	rm -f $${HOME}/.timeclock.yml

uninstall: removeBinary removeConfig

clean:
	rm -rf dist
	rm -rf build
	rm -rf __pycache__
	rm -f cli.spec