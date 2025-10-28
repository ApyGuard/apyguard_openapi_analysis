# Changelog

All notable changes to the OpenAPI Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] - 2025-09-27

### Added
- 🚀 Enhanced OpenAPI specification analysis
- 🛡️ Improved security checks and OWASP API Security Top 10 implementation
- 📚 Better documentation quality assessment
- ✅ Comprehensive best practice validation
- 🔧 Updated Docker image with latest improvements

## [1.0.4] - 2025-XX-XX

### Changed
- 🔧 Various stability improvements
- 📊 Enhanced complexity and maintainability scoring

## [1.0.3] - 2025-XX-XX

### Added
- 🛡️ Enhanced OWASP API Security Top 10 checks
- 📈 Improved performance analysis

## [1.0.2] - 2025-XX-XX

### Fixed
- 🔧 Docker container to work correctly with GitHub Actions working directory
- 🔧 Path resolution for local OpenAPI files
- 🔧 Container stability across different environments

### Added
- 📚 Comprehensive feature documentation and accurate output descriptions
- 🛡️ Enhanced OWASP API Security Top 10 implementation with all 10 checks
- 📊 Comprehensive analysis categories and improved scoring algorithms

## [1.0.1] - 2025-XX-XX

### Added
- 🆕 Repository Analysis: Analyze entire repositories for OpenAPI files
- 🆕 Auto-Discovery: Automatically finds OpenAPI files in repositories
- 🆕 Output Formats: JSON and summary output formats
- 🆕 Compliance Checks: Added GDPR, HIPAA, and PCI-DSS compliance analysis
- 🆕 Advanced Analytics: Implemented complexity and maintainability scoring

## [1.0.0] - 2025-XX-XX

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
