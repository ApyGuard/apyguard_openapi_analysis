# Security Policy

We take the security of **OpenAPI Analyzer** seriously. This document explains how we handle vulnerabilities, supported versions, reporting procedures, and our commitments to users and researchers.

---

## 🔢 Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | ✅ Supported        |
| < 1.0   | ❌ Not Supported    |

---

## 🔒 Reporting a Vulnerability

If you discover a security vulnerability, we ask you to report it responsibly so we can investigate and fix it quickly.

### How to Report
1. **DO NOT** open a public GitHub issue for security vulnerabilities.  
2. **DO NOT** disclose the vulnerability publicly until we’ve confirmed and fixed it.  
3. **DO** report security issues privately using one of these methods:

#### Option 1: GitHub Security Advisories (Recommended)
- Go to the [Security tab](https://github.com/ApyGuard/openapi_analyzer/security) in this repository.  
- Click **“Report a vulnerability”**.  
- Complete the advisory form with details of the issue.  

#### Option 2: Direct Contact
- Email: [security@apyguard.com](mailto:security@apyguard.com)  
- Subject line: **SECURITY**  
- Provide as much detail as possible (see below).  

### What to Include
When reporting, please include:  
- **Description**: Clear summary of the vulnerability  
- **Impact**: Potential consequences if exploited  
- **Steps to Reproduce**: Exact steps to replicate the issue  
- **Affected Versions**: List of affected versions  
- **Suggested Fix**: Optional recommendations  
- **Contact Info**: How we can reach you for follow-up  

---

## 🛡️ Our Response Process

When you report a vulnerability, we will:  
1. **Acknowledge** your report within **48 hours**.  
2. **Investigate** thoroughly to confirm the issue.  
3. **Develop and test** a fix if validated.  
4. **Release** a security update as soon as possible.  
5. **Credit** you in advisories (unless you prefer anonymity).  
6. **Notify** you when the fix is available.  

---

## 🏆 Researcher Recognition

We value contributions from the security community:  
- **Hall of Fame**: Researchers may be listed in security advisories.  
- **Credit**: Proper recognition for responsible disclosure.  
- **Acknowledgment**: Significant contributions may be highlighted in release notes.  

---

## 🔍 Scope

This policy covers:  
- **OpenAPI Analyzer GitHub Action** (core functionality)  
- **Dependencies** (when directly bundled or affecting security)  
- **Infrastructure** (GitHub Actions runners and containers)  
- **Documentation** (security-related guidance and examples)  

---

## 🚫 Out of Scope

The following are *not* considered valid security reports:  
- Social engineering (phishing, etc.)  
- Physical attacks on systems  
- DoS or spam that doesn’t lead to data exposure  
- Issues only affecting unrelated third-party dependencies  

---

## 📜 Responsible Disclosure

We follow responsible disclosure principles:  
- **90-day timeline**: Critical vulnerabilities are targeted to be fixed within 90 days.  
- **Coordinated disclosure**: We work with researchers on safe public disclosure timelines.  
- **Good faith protection**: No legal action against researchers acting responsibly.  
- **Transparent updates**: We’ll keep you informed during investigation and resolution.  

---

## 🔧 Security Best Practices

To keep users safe, we enforce:  
- **Minimal permissions**: GitHub Action requests only what it needs.  
- **Secure defaults**: Secure-by-default configurations.  
- **Dependency management**: Regular updates and vulnerability scans.  
- **Encrypted communication**: All transmissions use HTTPS.  
- **No sensitive data collection**: We never collect API keys, passwords, or private repository content.  

---

## 📞 Contact

For security-related issues:  
- **Vulnerabilities**: Use GitHub Security Advisories or email [security@apyguard.com](mailto:security@apyguard.com).  
- **General Questions**: [GitHub Discussions](https://github.com/ApyGuard/openapi_analyzer/discussions).  
- **Documentation**: [Security Wiki](https://github.com/ApyGuard/openapi_analyzer/wiki/Security).  

---

**Thank you for helping us keep OpenAPI Analyzer secure!** 🛡️  

---

*Last Updated: September 2025*
