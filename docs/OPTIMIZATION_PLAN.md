# Our Plan

## Step 1

First, 4 companies receive the complaints. Their ONLY job is to fill out a template that will provide as much info to Laya as possible, without having to make them look through every system.

Then, Laya uses their info to categorize within the five categories.

Then, Laya decides how urgent the request is. This does not need to use the historic data, because their way of deciding if something was urgent was not that good. This will be displayed on our app and dashboard.

Now, when someone needs to solve complaints, they can go to the dashboard, select their specific role (for example, Billing), then they can click Get Action Items, which invokes the Agentic + Ollama call.

Here is the big architecture change: the tools will pull the data it needs that it thinks is important, but this data is super tedious and it lives on these different systems. For example, Aurora Billing has tedious billing info tied to an account, while Helix has all account summary — but the Local LLM can and will get this data itself. This means we don't need humans looking through the systems in the first step of the process.
