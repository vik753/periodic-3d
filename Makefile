.PHONY: check py-syntax whitespace

## Lightweight checks that run without installed project dependencies.
check: whitespace py-syntax

whitespace:
	@git diff --check HEAD -- . && echo "whitespace: ok"

py-syntax:
	@files="$$(git ls-files '*.py')"; \
	if [ -n "$$files" ]; then python3 -m py_compile $$files && echo "python syntax: ok"; \
	else echo "python syntax: no files"; fi
