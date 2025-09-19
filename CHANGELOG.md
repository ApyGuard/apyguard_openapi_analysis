# Changelog

All notable changes to the OpenAPI Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive README with usage examples
- Privacy policy for marketplace compliance
- Security policy for vulnerability reporting
- Automated release workflow
- MIT license

### Changed
- Enhanced action.yml with proper outputs and branding
- Updated analyzer.py to set GitHub Actions outputs

## [1.0.0] - 2025-10-XX

### Added
- Initial release of OpenAPI Analyzer
- Basic OpenAPI specification validation
- Comprehensive best practice checks including:
  - Security analysis (global and operation-level)
  - Documentation quality assessment
  - Schema validation and composition checks
  - Operation ID uniqueness validation
  - Parameter and response validation
  - Server definition checks
- Support for OpenAPI 3.0+ and Swagger 2.0
- JSON and YAML format support
- GitHub Actions integration with outputs
- Docker containerization
- Comprehensive error handling and suggestions

### Features
- **Security Analysis**: Identifies missing security definitions and authentication
- **Documentation Quality**: Checks for missing descriptions, examples, and proper schemas
- **Best Practices**: Validates operation IDs, HTTP status codes, and content types
- **Schema Validation**: Ensures proper schema definitions and composition
- **Comprehensive Reporting**: Provides actionable suggestions for improvement

### Technical Details
- Built with Python 3.x
- Uses `requests` for HTTP requests
- Supports `openapi-spec-validator` for specification validation
- Docker-based execution for consistent environments
- GitHub Actions outputs for integration with workflows

---

## Version History

- **v1.0.0**: Initial release with core functionality
- **v0.1.0**: Development and testing phase

## Support

For support and questions, please use the GitHub Issues or Discussions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
