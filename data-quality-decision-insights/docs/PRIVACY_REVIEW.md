# Presentation package privacy review

Neutral title and package name. Excluded original brand identifiers, original domain-specific sample data, historical analyses, provider/storage settings, Git history, bytecode and build caches. The original archive is preserved separately.

Replacement CSV and generated outputs are fictional. API and frontend default to loopback networking. Backend storage is local. No model calls or external storage are included. Dependency lockfiles contain ordinary package-registry URLs.

API key configuration uses environment variables; the frontend receives an optional key from manual session input rather than an embedded build-time secret. Data endpoints check the optional key when configured. Runtime files are not encrypted or isolated by user. Loopback development without a key is not authenticated hosting.

Source and documentation scans check original brands, original domain references, hosting identities, credential patterns and email patterns. Generated demo checks exclude remote resources and JavaScript. Scope is this package, not existing repositories or original history.

Keep the GitHub repository Private. Do not add runtime uploads, real exports, credentials or development environment files. Source access, a live demo and documentation are separate sharing decisions.
