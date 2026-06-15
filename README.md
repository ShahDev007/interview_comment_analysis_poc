# Comment Moderation Challenge

`comments.json` contains a sample dump of fictional comments on posts from our websites.

Your job is to build an application/process/system that has read-only access to this dataset and aids our moderation team in managing the volume of user-generated content (UGC) coming into our communities.

For each comment, the output should classify:

- **moderation:** Pass | Fail
- **user_type:** Patient | Caregiver | Healthcare Provider | Other

Build a local proof of concept that demonstrates to the business that this project will help them save time moderating content. Part of the goal is to show the business the value that LLMs and AI tooling bring here — what these tools make possible beyond simple rules or keyword matching, and why that's worth investing in. Once the business is convinced it works, we'll deploy the app to a hosted environment.

## Constraints

- **Mock all LLM calls.** We won't provision real API keys for this exercise, so no calls should hit a live LLM provider. Stub the model behind an interface so the whole thing runs locally, but design that boundary so a real LLM can be dropped in later with minimal changes. How you structure that seam is something we're interested in.

How you get there is up to you. The tools you choose, the design, and the criteria you apply are part of what we're evaluating, so document the decisions and assumptions you make along the way.
