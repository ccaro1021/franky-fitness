What is a virtual environment and why does it exist?
* A virtual environment is an isolated package folder for a specific project. It exists so that packages installed for one project don't affect other projects or the system Python that macOS relies on."
What does git push actually do?
* Git push uploads my local commits to the remote repository on GitHub. It synchronizes my local main branch with GitHub's copy of main, so both are up to date.
Why is the API key in .env and not in the Python file?
* This is a secrets protocol that prevents leaking sensitive information. When this information is leaked people can use my credits.
What's the difference between temperature=0 and temperature=1?
* Temperature=0 means that the highest propability word/token will be used always. This is used when you want more consistent answers. Temperature=1 will allow for words that don't have the highest probability to appear, in other words it allows for more randomness/creativity.
What do input_tokens and output_tokens tell you?
* input_tokens tells me the amount of tokens I used with my system prompt and message.content. Output_tokens tells me how many tokens were used in the response to my input. Output_tokens are more expensive than input tokens. Full conversation history also counts towards input tokens.
What does the system parameter do and why does it matter?
* The system parameter defines the agent's identity, personality, and rules before the conversation starts. It matters because it's the difference between a generic response and one tailored to your specific use case
What's one thing that surprised you this week?
* I feel like I'm picking all of the concepts up rather quickly because of my experience building Rovo agents. The meat of my learning is operational, debugging when python couldn't read my .env file or path issues with vscode.