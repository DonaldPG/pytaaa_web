<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements
	- Project is a FastAPI web app for stock trading models.
	- 5 models + 1 meta-model (monthly switching).
	- Portfolio has ~7 stocks each, updated monthly.
	- Stocks from Nasdaq 100 or S&P 500.
	- Existing logic in `PyTAAA.master`.
	- Infrastructure: FastAPI, PostgreSQL, SQLAlchemy, Docker.

- [ ] Scaffold the Project
	- Create directories and initial files.

- [ ] Customize the Project
	- Implement models, schemas, and API routes.

- [ ] Install Required Extensions
	- None specified.

- [ ] Compile the Project
	- Install dependencies and run.

- [ ] Create and Run Task
	- Set up `tasks.json`.

- [ ] Launch the Project
	- Start the FastAPI server and Postgres.

- [ ] Ensure Documentation is Complete
	- README.md, spec.md, LOG.md, ROADMAP.md, refinement_guide.md.
