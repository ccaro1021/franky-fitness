# Privacy Policy — Franky Fitness

**Last updated:** August 2, 2026

This policy describes how Franky Fitness ("the app," "we") handles data obtained through its integration with the WHOOP API.

## Data We Access

With your authorization via WHOOP's OAuth flow, Franky Fitness accesses the following data from your WHOOP account:

- Recovery data
- Sleep data
- Workout data
- Physiological cycle data
- Profile information
- Body measurement data

## How We Use Your Data

Your WHOOP data is used to personalize the meal planning and exercise recommendations Franky Fitness generates for you. To produce these recommendations, relevant data is sent via API to Anthropic's Claude models, which process it to generate your personalized plans. Anthropic acts as our AI processing provider for this purpose.

We do not use your data for any purpose beyond generating your personalized recommendations, and we do not sell your data.

## Data Sharing

Your data is shared with the following third party solely to provide the app's functionality:

- **Anthropic** — receives relevant WHOOP data via API to generate personalized meal and exercise recommendations.

We do not share your data with any other third party, and we do not use it for advertising or marketing purposes.

## Data Storage

OAuth access and refresh tokens are stored in our PostgreSQL database and retained until you revoke access via the WHOOP app or contact us to request deletion. WHOOP data retrieved through the API is not stored persistently — it is processed in real time by Anthropic's Claude models to generate your personalized recommendations and is not written to our database.

## Your Controls

You can revoke Franky Fitness's access to your WHOOP data at any time through the WHOOP app (Settings) or by contacting us directly. Revoking access will stop all further data collection.

## Contact

Questions about this policy or your data can be directed to: Christopher.ben.caro@gmail.com

---

*This is a single-developer personal project, not a commercial product. This policy is intended to be accurate and transparent about data handling, not a substitute for formal legal review if this app is ever offered to other users.*
