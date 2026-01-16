# Refinement Guide for AI Agents

## Core Principles
1. **Consistency**: Always refer to `spec.md` for the database schema and entity names.
2. **Context Documentation**: Update `LOG.md` after any significant implementation steps.
3. **Modular Design**: Keep FastAPI routes clean by offloading logic to services or CRUD modules.
4. **Integration Focus**: Remember this is a dashboard for an *existing* trading system. The data source is the output of `PyTAAA.master`.

## Implementation Patterns
- **Database**: Use SQLAlchemy 2.0 async sessions (see `app/db/session.py`)
- **Schemas**: Use Pydantic v2 for all request/response models
- **Errors**: Use descriptive HTTP exceptions with status codes:
  - 404: Model/data not found
  - 422: Invalid date ranges or model names
  - 500: Database connection or parsing errors
- **Security**: Local deployment only (no auth required - runs on internal network)

## Handling Monthly Updates
- Rankings change at the start of each month.
- Ensure `PortfolioSnapshot` is linked to the correct month.
- Meta-model switching logic should be easily auditable by tracking `active_sub_model_id` in `PortfolioSnapshot`.

## Parsing Requirements

### Status File (`PyTAAA_status.params`)
- **Format**: `cumu_value: <timestamp> <base_value> <signal> <traded_value>`
- **Parser**: Simple `line.split()` after stripping prefix
- **Error Handling**: Skip malformed lines, log warning, continue
- **Test**: Must parse 5000 lines in <5s

### Holdings File (`PyTAAA_holdings.params`)
- **Format**: ConfigParser sections with space-separated lists
- **Special Case**: `trading_model: <name>` tag for meta-model
- **Parser**: Use `configparser.ConfigParser(strict=False)`
- **Error Handling**: Fail fast if [Holdings] section missing
- **Test**: Parse all 6 models' holdings files without errors

### Performance Store Locations
Each model's data lives in its own folder:
```
/Users/donaldpg/pyTAAA_data/
  naz100_pine/data_store/PyTAAA_status.params
  naz100_hma/data_store/PyTAAA_status.params
  ...
  naz100_sp500_abacus/data_store/PyTAAA_holdings.params  # Contains trading_model: tag
```

## Testing Standards
- **Unit Tests**: 80% coverage minimum for parsers and API routes
- **Integration Tests**: Full ingestion cycle with sample .params files
- **Performance Tests**: 
  - Import 1000 days in <5s
  - API response <500ms for 90-day queries
- **Error Cases**: Test malformed files, missing data, invalid dates
