.PHONY: run
run: 
	open -a safari.app http://localhost:8080/docs/index.html
	php -S localhost:8080
