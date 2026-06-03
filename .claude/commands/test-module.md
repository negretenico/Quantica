Run the tests for the Quantica module specified in $ARGUMENTS. Navigate to the correct directory and use the appropriate test command:
- Java modules (marketListener, markettransformer): `mvn test`
- Python modules (marketanalysis, marketbard): `python -m pytest`
- Go module (marketappendonly): `go test ./...`

Report a summary of results including any failures with their test names and error messages.
