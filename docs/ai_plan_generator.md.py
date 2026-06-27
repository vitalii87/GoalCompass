# AI Plan Generator Concept

## Purpose
'''
AI Plan Generator is a future GoalCompass module that helps users convert broad goals into structured, trackable plans.

The module is not part of the core tracking engine. It generates configuration files that the core engine can validate and use.

## Core Idea

User may have a goal but no concrete plan.

Examples:

- Get a QA job
- Reach German B1
- Improve physical shape
- Reduce gaming time
- Build a personal project
- Improve sleep and health

AI Plan Generator should help create:

- goals
- progress rules
- daily or weekly targets
- limits
- manual presets
- weekly schedule
- suggested alerts
- coach behavior settings

## Architecture Principle

AI must not modify application code.

AI generates JSON configuration only.

Flow:

User goal
→ short questionnaire
→ AI-generated plan JSON
→ validator
→ preview
→ user approval
→ save to user_config

## Modes

### Manual Mode

User edits configuration manually.

### AI-Assisted Mode

AI generates configuration, but user reviews and approves it.

### Full AI Coach Mode

AI analyzes real progress and proposes adjustments over time.

## Generated Files

Possible generated files:

```text
data/user_config/primary.json
data/user_config/manual_presets.json
data/user_config/schedule.json
'''

