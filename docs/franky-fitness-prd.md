# Franky Fitness — Product Requirements Document

---

## Problem Statement

People who want to eat healthier, exercise consistently, and stay organized around their wellness goals struggle to maintain the habits necessary to do so. Planning nutritious meals for the week, building a grocery list from those meals, and designing appropriate workout routines are all time-consuming tasks that require domain knowledge most people don't have. Generic meal and fitness apps offer templated plans that don't reflect individual goals, dietary restrictions, body composition, or fitness level. Users end up abandoning plans that don't fit their lives, reverting to unhealthy defaults, and feeling like health and wellness require more effort than they're worth.

There is no intelligent, conversational tool that understands a user as an individual — their BMI, their dietary constraints, their fitness goals, their history of what worked and what didn't — and adapts its advice over time based on what they actually experience.

---

## Solution

Franky Fitness is a free, web-based AI wellness assistant powered by Claude. It gives every user a personalized, conversational experience for meal planning, grocery list generation, and exercise programming. Users create an account, provide their profile details (dietary restrictions, fitness goals, BMI), and have natural conversations with Franky to generate weekly plans tailored specifically to them.

Franky gets smarter over time. It learns from user feedback on past meals and workouts — what they liked, what they skipped, what didn't work for their body — and incorporates that history into future suggestions. The result is a wellness partner that genuinely knows the user and improves with every interaction.

---

## User Stories

### Onboarding and Account Management

1. As a new user, I want to create an account with my email and password, so that my data and history are saved and private to me.
2. As a new user, I want to complete an onboarding flow that captures my dietary restrictions, fitness goals, and physical stats, so that Franky's first suggestions are already relevant to me.
3. As a new user, I want to enter my height and weight during onboarding, so that Franky can calculate and store my BMI for personalized recommendations.
4. As a returning user, I want to log in to my account, so that I can access my history and continue where I left off.
5. As a logged-in user, I want to view and edit my profile, so that I can update my dietary restrictions, goals, or physical stats when they change.
6. As a logged-in user, I want Franky to recalculate my BMI automatically when I update my height or weight, so that my profile stays accurate without manual calculation.
7. As a logged-in user, I want to see my current BMI displayed on my profile, so that I can track how it changes over time.
8. As a logged-in user, I want to change my password, so that I can maintain the security of my account.
9. As a logged-in user, I want to delete my account and all associated data, so that I have full control over my personal information.
10. As a logged-in user, I want to log out of my account, so that my data is protected on shared devices.

### Meal Planning

11. As a logged-in user, I want to start a conversation with Franky to request a weekly meal plan, so that I get personalized meal suggestions without having to research recipes myself.
12. As a logged-in user, I want Franky to consider my dietary restrictions when generating meal plans, so that I never receive suggestions that include foods I can't or don't eat.
13. As a logged-in user, I want Franky to consider my fitness goals (e.g., muscle building, weight loss, general health) when generating meal plans, so that the macros in my plan support what I'm working toward.
14. As a logged-in user, I want Franky to include approximate calories, protein, carbs, and fat for each meal, so that I can make informed decisions about what I eat.
15. As a logged-in user, I want Franky to organize meal plans by day and meal type (breakfast, lunch, dinner, snacks), so that I can easily follow the plan throughout the week.
16. As a logged-in user, I want to tell Franky how many meals per day I want to plan for, so that the plan fits my actual eating habits.
17. As a logged-in user, I want to tell Franky how much time I have to cook on weeknights vs. weekends, so that I get realistic suggestions I'll actually follow.
18. As a logged-in user, I want Franky to factor in ingredients I already have at home, so that my grocery spend is minimized and food waste is reduced.
19. As a logged-in user, I want to ask Franky to swap out a specific meal I don't like, so that I can refine the plan without regenerating it entirely.
20. As a logged-in user, I want to save a generated meal plan to my history, so that I can reference it later in the week.
21. As a logged-in user, I want to view past meal plans in my history, so that I can revisit or repeat plans that worked well.
22. As a logged-in user, I want to rate individual meals with a thumbs up or thumbs down, so that Franky learns what I like and improves future suggestions.
23. As a logged-in user, I want to leave a short note on a meal rating (e.g., "too spicy" or "loved this"), so that Franky has more context for personalization.
24. As a logged-in user, I want Franky to avoid suggesting meals I've previously rated negatively, so that I don't receive the same bad suggestions repeatedly.
25. As a logged-in user, I want Franky to suggest meals I've previously rated positively more often, so that my plan reflects my proven preferences.
26. As a logged-in user, I want Franky to generate variety across weeks, so that I don't receive the same plan repeatedly even if my preferences are consistent.
27. As a logged-in user, I want Franky to acknowledge if I mention a health condition or medication, so that I receive a note to consult a clinician rather than specific medical dietary advice.

### Grocery List Generation

28. As a logged-in user, I want Franky to automatically generate a grocery list from my weekly meal plan, so that I don't have to manually extract ingredients.
29. As a logged-in user, I want the grocery list to be organized by store section (produce, protein, dairy, pantry, frozen), so that I can shop efficiently without backtracking.
30. As a logged-in user, I want ingredients that appear across multiple meals to be consolidated with the correct combined quantity, so that I don't buy duplicate items.
31. As a logged-in user, I want to tell Franky what I already have at home before it generates the list, so that I only see items I actually need to buy.
32. As a logged-in user, I want to manually check off items on my grocery list as I shop, so that I can track what I've already picked up.
33. As a logged-in user, I want to add items to my grocery list manually, so that I can include household essentials that aren't part of the meal plan.
34. As a logged-in user, I want to remove items from my grocery list, so that I can adjust if I already have something or change my mind.
35. As a logged-in user, I want to view past grocery lists in my history, so that I can reference what I bought in previous weeks.
36. As a logged-in user, I want to copy a past grocery list as a starting point for a new week, so that I can reuse it with minimal adjustments.

### Exercise Planning

37. As a logged-in user, I want to start a conversation with Franky to request a weekly workout plan, so that I get a structured exercise routine tailored to my goals.
38. As a logged-in user, I want Franky to factor in my fitness goal (e.g., build muscle, lose weight, improve endurance, general fitness) when generating a workout plan, so that the exercises and volume are appropriate for what I'm trying to achieve.
39. As a logged-in user, I want to tell Franky how many days per week I can work out, so that the plan fits my schedule.
40. As a logged-in user, I want to tell Franky how long each session can be, so that the plan is realistic for my available time.
41. As a logged-in user, I want to tell Franky what equipment I have access to (e.g., home gym, commercial gym, no equipment), so that the exercises are achievable for my setup.
42. As a logged-in user, I want Franky to include warm-up and cooldown guidance in each workout, so that I reduce my risk of injury.
43. As a logged-in user, I want Franky to include sets, reps, and RPE (rate of perceived exertion) or duration for each exercise, so that I know how hard to push.
44. As a logged-in user, I want Franky to include active recovery or rest day guidance, so that I understand how to recover properly.
45. As a logged-in user, I want Franky to flag if I mention a current injury or physical limitation, so that the plan avoids exercises that could make it worse and recommends I consult a clinician if appropriate.
46. As a logged-in user, I want to tell Franky which exercises I don't like or can't do, so that the plan works around my preferences and limitations.
47. As a logged-in user, I want to save a generated workout plan to my history, so that I can reference it throughout the week.
48. As a logged-in user, I want to view past workout plans in my history, so that I can revisit or repeat routines that worked well.
49. As a logged-in user, I want to rate individual workouts or exercises with a thumbs up or thumbs down, so that Franky learns what resonates with me.
50. As a logged-in user, I want Franky to suggest workout plan progressions over time (e.g., increase weight or volume in subsequent weeks), so that my training adapts as I get stronger.

### Conversational Interface

51. As a logged-in user, I want to have a multi-turn conversation with Franky, so that I can refine a plan through back-and-forth dialogue rather than filling out a form.
52. As a logged-in user, I want Franky to ask clarifying questions when my request is ambiguous, so that the output is accurate to my intent.
53. As a logged-in user, I want Franky to remember context from earlier in our conversation, so that I don't have to repeat myself mid-session.
54. As a logged-in user, I want Franky to maintain a consistent, encouraging but direct personality across all interactions, so that talking to it feels natural and not robotic.
55. As a logged-in user, I want to be able to ask Franky follow-up questions about any plan it generates, so that I can understand why it made specific suggestions.
56. As a logged-in user, I want to start a new conversation session at any time, so that I can get a fresh plan without previous session context interfering.
57. As a logged-in user, I want the conversation interface to clearly distinguish between my messages and Franky's responses, so that the exchange is easy to read.

### History and Personalization

58. As a logged-in user, I want Franky to reference my meal and workout history when generating new plans, so that suggestions improve over time without me having to re-explain my preferences.
59. As a logged-in user, I want to view a history of all my generated plans in chronological order, so that I can track how my routines have evolved.
60. As a logged-in user, I want to filter my history by type (meal plans, grocery lists, workout plans), so that I can find what I'm looking for quickly.
61. As a logged-in user, I want to delete individual items from my history, so that I can remove plans that are no longer relevant.
62. As a logged-in user, I want Franky to notice patterns in my feedback over time (e.g., consistently rating high-protein dinners positively), so that new plans proactively reflect those patterns.
63. As a logged-in user, I want to see a summary of my preferences as Franky understands them, so that I can verify its model of me is accurate.
64. As a logged-in user, I want to correct Franky's understanding of my preferences directly, so that personalization errors don't persist.

---

## Implementation Decisions

### Architecture

- Franky is a web application with a FastAPI backend, a React frontend, and a PostgreSQL database. The backend handles all API calls to Claude and all data persistence.
- The AI layer is a multi-agent system built on the Anthropic SDK. A coordinator agent receives the user's conversational input and routes to one of three sub-agents: a meal planning agent, a grocery list agent, or an exercise planning agent. The grocery list agent always receives the meal plan as input before generating a list.
- Claude Sonnet is the model powering all agents. Model selection is not exposed to the user.
- The system prompt for each sub-agent is stored in a separate file from application code, so prompt changes do not require code deploys.

### User Profiles and Authentication

- Users authenticate with email and password. Passwords are hashed before storage; plaintext passwords are never stored.
- Each user has a profile record containing: name, email, height, weight, BMI (calculated server-side), dietary restrictions, and fitness goals.
- BMI is calculated on the server whenever height or weight is updated. The formula (weight in kg / height in meters squared) is applied server-side, not client-side.
- Dietary restrictions and fitness goals are stored as structured fields, not freeform text, to ensure they can be reliably injected into agent prompts.

### Personalization

- User feedback (thumbs up/down + optional note) on individual meals and workouts is stored in a feedback table keyed to the plan item and user ID.
- Before each agent call, the user's recent feedback history is retrieved from the database and injected into the system prompt as context. This is the primary personalization mechanism — the model is not fine-tuned.
- A preference summary (positive signals, negative signals, patterns) is derived from feedback history and stored per user. It is updated after each feedback submission and injected into the system prompt on every agent call.
- The preference summary is surfaced to the user in their profile view as a plain-language description of what Franky understands about them.

### Data Models

- **users:** id, email, password_hash, name, created_at
- **profiles:** id, user_id (FK), height, weight, bmi, dietary_restrictions (JSON array), fitness_goals (JSON array), updated_at
- **plans:** id, user_id (FK), type (meal_plan | grocery_list | workout_plan), content (JSON), created_at
- **plan_items:** id, plan_id (FK), item_type, content (JSON), position
- **feedback:** id, user_id (FK), plan_item_id (FK), rating (positive | negative), note (nullable), created_at
- **preference_summaries:** id, user_id (FK), summary (JSON), updated_at
- **agent_runs:** id, user_id (FK), agent_type, input_tokens, output_tokens, latency_ms, created_at

### Agent Design Decisions

- Each sub-agent receives: the user's profile (restrictions, goals, BMI), their preference summary, and the user's conversational input for the session.
- The grocery list agent additionally receives the current meal plan as structured input.
- All agent outputs are structured JSON conforming to defined schemas (MealPlan, WorkoutPlan, GroceryList). The coordinator is responsible for parsing and validating structured output before returning it to the frontend.
- Agent runs are logged to the agent_runs table for observability. Every call logs which agent ran, token usage, and latency. This is separate from plan storage.
- The coordinator handles errors from sub-agents gracefully — if a sub-agent call fails, it returns a user-facing error message rather than crashing the session.

### Grocery List Logic

- Ingredient consolidation (combining quantities of the same ingredient across multiple meals) is handled by the grocery list agent, not by application code. The agent receives the full structured meal plan and is instructed to deduplicate and combine quantities.
- Store section categorization (produce, protein, dairy, pantry, frozen) is part of the GroceryList schema. Each item has a category field. The agent is responsible for categorization.

### Conversational State

- Conversation history (the messages list) is maintained in the frontend session state for the duration of an active conversation. It is not persisted to the database.
- When a user starts a new conversation, history is cleared and a fresh session begins.
- The user's profile context and preference summary are injected fresh into the system prompt on every call — they do not rely on conversation history for personalization.

### Feedback and Personalization Schemas (from prototype)

The following type shapes encode the feedback and preference structures:

```
Feedback:
  user_id: string
  plan_item_id: string
  rating: "positive" | "negative"
  note: string | null

PreferenceSummary:
  liked_meals: string[]
  disliked_meals: string[]
  liked_workouts: string[]
  disliked_workouts: string[]
  patterns: string[]  // e.g. "Consistently rates high-protein dinners positively"
```

---

## Testing Decisions

### What makes a good test

A good test verifies the external behavior of a module — what it returns or what effect it produces — without depending on how it produces that result. Tests should not assert on internal implementation details (e.g., which sub-function was called, how many intermediate steps occurred). This keeps tests stable as the implementation evolves.

Tests should use realistic inputs (real dietary restrictions, real feedback histories) rather than minimal stubs, because agent behavior depends heavily on the richness of context.

### Modules to test

**User profile module:**
- BMI is calculated correctly given valid height and weight inputs
- BMI is recalculated when height or weight is updated
- Dietary restrictions and fitness goals are stored and retrieved as structured data, not freeform strings
- Profile updates are rejected if required fields are missing or of the wrong type

**Authentication module:**
- A user can register with a valid email and password
- Duplicate email registration is rejected
- Login with correct credentials returns an authenticated session
- Login with incorrect credentials is rejected
- Password storage never contains plaintext

**Meal planning agent:**
- Generated meal plans contain all required fields (day, meal type, name, macros)
- Meals do not include ingredients that violate the user's dietary restrictions
- Plans reflect the user's feedback history — previously negatively-rated meals do not appear in new plans when that history is injected
- Plans include macros for every meal

**Grocery list agent:**
- Generated lists include all ingredients from the provided meal plan
- Duplicate ingredients are consolidated with combined quantities
- Each item includes a store section category
- Items already marked as "in pantry" by the user are excluded

**Exercise planning agent:**
- Generated plans match the requested number of workout days
- Each session includes warm-up, workout, and cooldown sections
- Each exercise includes sets, reps/duration, and RPE
- Plans avoid exercises flagged by the user as unavailable due to injury or preference

**Feedback module:**
- A rating is stored with the correct user_id and plan_item_id
- Preference summaries are updated after a feedback submission
- The updated summary correctly reflects the new feedback

**Agent runs logging:**
- Every agent call produces an agent_runs record
- The record contains the correct agent type, token counts, and latency

### Prior art

Tests for the agent modules follow the same output-validation pattern as the `eval_franky.py` eval suite already built in the project: run the agent with controlled inputs, assert on the structure and content of the output. LLM-graded evals (using Claude as a grader) are appropriate for subjective assertions (e.g., "does this meal plan respect the user's dietary restrictions?"). Code-based assertions are appropriate for structural checks (e.g., "does the plan contain exactly 7 days?").

---

## Out of Scope

- **Social features:** sharing plans with other users, following other users, community recipes or workouts.
- **Integrations with third-party services:** fitness trackers (Fitbit, Garmin, Apple Health), grocery delivery apps, calendar apps.
- **Calorie or macro tracking:** logging what you actually ate vs. what was planned. Franky generates plans; it does not track execution.
- **Progress tracking over time:** weight trend charts, strength progression graphs, body composition tracking.
- **Push notifications or reminders:** reminding users to cook, shop, or work out.
- **Image-based features:** uploading photos of meals, scanning barcodes, photographing a pantry.
- **Recipe storage:** saving individual recipes to a personal library outside of a plan.
- **Paid tiers or premium features:** the product is free. Monetization is not in scope.
- **Native mobile apps:** the product is web-based. Mobile-responsive web is in scope; native iOS or Android apps are not.
- **Multi-user household accounts:** each account belongs to one person. Couple or family sharing is not in scope.
- **Medical nutrition therapy:** Franky does not diagnose conditions, prescribe diets for medical conditions, or replace clinical nutrition advice. When a user mentions a specific medical condition, Franky provides a note to consult a clinician.

---

## Further Notes

**Safety guardrails in system prompts:** The system prompt for each agent must include explicit instructions to avoid medical claims, include a "consult a clinician" note when medical conditions or injuries are mentioned, and avoid exercises that conflict with stated physical limitations. These are behavioral guardrails, not application-layer filters — they are enforced through the prompt and should be tested as part of agent testing.

**BMI as a signal, not a prescription:** BMI is stored and used as one context signal for personalization. Franky should not present BMI as a diagnostic tool or make claims about a user's health status based on BMI alone. The system prompt should instruct agents to use BMI as background context only.

**Preference injection latency:** Injecting a user's full feedback history into every prompt will grow token costs as history accumulates. The preference summary (a distilled version of feedback history) is the primary injection mechanism to keep token usage manageable. The raw feedback table exists for deriving the summary, not for direct injection.

**Eval-first approach for agent quality:** Before the product is used by users beyond the initial test group, an eval suite should be run to confirm agents meet quality thresholds. Recommended minimum: pass^3 (succeeds on all of 3 runs) on the core behaviors for each agent. Single-run success rates are insufficient for a product whose value depends on consistency.

**CLAUDE.md for developer context:** A CLAUDE.md file at the project root should document the agent architecture, the system prompt file locations, and the conventions for injecting user context. This enables Claude Code (used as the primary build tool) to maintain architectural consistency as the codebase grows.
