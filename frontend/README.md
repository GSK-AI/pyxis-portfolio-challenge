# Pyxis - Investment Game - Frontend

This guide will help developers set up, run, and understand the frontend, built with Next.js. It covers everything from installation to development workflows.

## Useful Links

- [Project Repositor: GitHub](https://github.com/gsk-tech/pyxis-portfolio-challenge)

## Prerequisites

Before you begin, make sure you have the following installed:

- **[Node.js](https://nodejs.org/)** (v16.x or above) – JavaScript runtime.
- **[pnpm](https://pnpm.io/)** – Fast, disk space-efficient package manager.

To verify installations, run the following commands:

```bash
node -v    # Should return v18.x or above
npm -v     # Verify npm installation
pnpm -v    # Verify pnpm installation
```

## Setting up the Frontend

If the above dependencies fails, please follow the following steps to install all the required tools and libraries in order to run the project locally.

### 01. Install NVM (Node Version Manager)

NVM allows you to easily install and manage multiple Node.js versions. <https://github.com/nvm-sh/nvm>

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# OR
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
```

After installation, load nvm:

```bash
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
```

```bash
source ~/.bashrc    # for bash
# OR
source ~/.zshrc     # for zsh
```

Please run `nvm -v` to see if the nvm is loaded correctly.

### 02. Install Node.js

Once `nvm` is installed now we can use nvm to install `Node.js`

```bash
nvm install 22
```

To verify installations, run the following commands:

```bash
node -v    # Should return v18.x or above
npm -v     # Verify npm installation
```

### 03. Allow GSK SSL Certificate

Please run the following command to allow `npm` to install packages. This is required on GSK network

```bash
export NODE_EXTRA_CA_CERTS=gsk-cert.crt
# gsk-cert.crt is available in frontend directory in this project
```

### 04. Install pnpm

```bash
npm install -g pnpm
```

To verify installations, run the following command:

```bash
pnpm -v    # Verify pnpm installation
```

After completing these steps, you can run the project.

## Configure Environment Variables

Create a `.env` file in the root of the frontend directory. Copy the example from `.env.example`

```bash
touch .env
```

Add the following variables:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8080  # URL for the local FastAPI backend
NEXT_PUBLIC_BACKEND_URL_GAME=http://localhost:8000 # URL for the local FastAPI backend for investment game
```

Ensure the FastAPI backend is running locally at the specified URL.

## Run the Frontend Locally

If everything is installed correctly, you can run the project with:

```bash
pnpm install    # Install project dependencies
pnpm dev        # Run Development Server
```

The application will be available at <http://localhost:3000>

---

## Common Issues & Fixes

### 01. Issue: "Cannot connect to backend API"

Fix:

- Confirm the FastAPI backend is running locally.
- Verify NEXT_PUBLIC_BACKEND_URL in `.env`
- Check browser console for CORS errors.

### 02. Issue: "Port 3000 is already in use"

Fix:

- Run the app on a different port:

```bash
PORT=3001 pnpm dev
```

### 03. Issue: "Module not found" or dependency errors

Fix:

- Delete node_modules and reinstall dependencies:

```bash
rm -rf node_modules package-lock.json

pnpm install
```

---

## Helpful Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ESLint Documentation](https://eslint.org/docs/latest/)

## Contributors

_Interested in contributing? Feel free to fork the repository, submit a pull request, or open an issue!_

We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for writing clear and structured commit messages.

--

Best

**Sahil David** – <sahil.x.david@gsk.com>  
Feel free to reach out with any questions or suggestions!
