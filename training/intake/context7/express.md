# Express.js

Express is a minimal and flexible Node.js web application framework that provides routing, middleware composition, and HTTP utility methods for building web APIs and applications.

## Middleware Overview

Middleware functions execute during the request-response cycle and have access to the request object, response object, and the next function. They are mounted using `app.use()` and execute in the order they are defined:

```javascript
const express = require('express')
const app = express()

// Application-level middleware (runs on every request)
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.url}`)
  req.requestTime = Date.now()
  next()
})

// Built-in middleware
app.use(express.json())                          // Parse JSON request bodies
app.use(express.urlencoded({ extended: true }))  // Parse URL-encoded bodies
app.use(express.static('public'))                // Serve static files

// Path-specific middleware
app.use('/api', (req, res, next) => {
  const apiKey = req.headers['x-api-key']
  if (!apiKey || apiKey !== 'valid-key') {
    return res.status(401).json({ error: 'Invalid API key' })
  }
  next()
})

// Multiple middleware on a single route
const authenticate = (req, res, next) => {
  const token = req.get('Authorization')
  if (!token) return res.status(401).json({ error: 'No token' })
  req.userId = decodeToken(token)
  next()
}

const authorize = (...roles) => (req, res, next) => {
  if (!roles.includes(req.userRole)) {
    return res.status(403).json({ error: 'Forbidden' })
  }
  next()
}

app.delete('/users/:id', authenticate, authorize('admin'), (req, res) => {
  res.json({ deleted: req.params.id })
})

app.listen(3000)
```

## 404 Handling Middleware

Catch unmatched routes by placing a middleware after all route definitions:

```javascript
const express = require('express')
const app = express()

// Define routes first
app.get('/', (req, res) => {
  res.json({ message: 'Home' })
})

app.get('/api/users', (req, res) => {
  res.json([{ id: 1, name: 'Alice' }])
})

// 404 handler - must come AFTER all routes
// This catches any request that did not match a defined route
app.use((req, res, next) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Cannot ${req.method} ${req.originalUrl}`,
    status: 404
  })
})

// Error handler comes after 404 handler
app.use((err, req, res, next) => {
  console.error(err.stack)
  res.status(500).json({ error: 'Internal Server Error' })
})

app.listen(3000)
```

## Error Handling Chain

Express uses a specific pattern for error handling middleware (4 parameters). Errors propagate through the middleware chain when passed to `next()`:

```javascript
const express = require('express')
const app = express()

app.use(express.json())

// Route that throws synchronously
app.get('/sync-error', (req, res) => {
  throw new Error('Sync failure')
})

// Route that passes error to next()
app.get('/async-error', async (req, res, next) => {
  try {
    const data = await fetchExternalService()
    res.json(data)
  } catch (err) {
    next(err)  // Pass error to error-handling middleware
  }
})

// Route with custom error
app.get('/items/:id', (req, res, next) => {
  const item = findItem(req.params.id)
  if (!item) {
    const err = new Error('Item not found')
    err.status = 404
    return next(err)
  }
  res.json(item)
})

// First error handler: log the error
app.use((err, req, res, next) => {
  console.error(`[${new Date().toISOString()}] ${err.message}`)
  console.error(err.stack)
  next(err)  // Pass to next error handler
})

// Second error handler: format response for API errors
app.use((err, req, res, next) => {
  if (req.path.startsWith('/api')) {
    return res.status(err.status || 500).json({
      error: err.message,
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    })
  }
  next(err)  // Pass to final handler for non-API routes
})

// Final error handler: generic HTML response
app.use((err, req, res, next) => {
  res.status(err.status || 500)
  res.send(`<h1>Error ${err.status || 500}</h1><p>${err.message}</p>`)
})

app.listen(3000)
```

## Custom Error-Handling Middleware

Build structured error handling with custom error classes:

```javascript
const express = require('express')
const app = express()

app.use(express.json())

// Custom error classes
class AppError extends Error {
  constructor(message, statusCode) {
    super(message)
    this.statusCode = statusCode
    this.isOperational = true
  }
}

class NotFoundError extends AppError {
  constructor(resource = 'Resource') {
    super(`${resource} not found`, 404)
  }
}

class ValidationError extends AppError {
  constructor(details) {
    super('Validation failed', 400)
    this.details = details
  }
}

// Async wrapper to catch promise rejections
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next)
}

// Routes using custom errors
app.get('/users/:id', asyncHandler(async (req, res) => {
  const user = await db.findUser(req.params.id)
  if (!user) throw new NotFoundError('User')
  res.json(user)
}))

app.post('/users', asyncHandler(async (req, res) => {
  const { name, email } = req.body
  const errors = []
  if (!name) errors.push('name is required')
  if (!email) errors.push('email is required')
  if (errors.length) throw new ValidationError(errors)

  const user = await db.createUser({ name, email })
  res.status(201).json(user)
}))

// Centralized error handler
app.use((err, req, res, next) => {
  // Operational errors (expected)
  if (err.isOperational) {
    return res.status(err.statusCode).json({
      status: 'error',
      message: err.message,
      ...(err.details && { details: err.details })
    })
  }

  // Programming errors (unexpected)
  console.error('UNEXPECTED ERROR:', err)
  res.status(500).json({
    status: 'error',
    message: 'Something went wrong'
  })
})

app.listen(3000)
```

## Route Rendering

Render HTML responses using template engines:

```javascript
const express = require('express')
const path = require('path')
const app = express()

// Set template engine
app.set('view engine', 'ejs')
app.set('views', path.join(__dirname, 'views'))

// Render a view with data
app.get('/', (req, res) => {
  res.render('index', {
    title: 'Home Page',
    users: [
      { name: 'Alice', role: 'admin' },
      { name: 'Bob', role: 'user' }
    ]
  })
})

// Render with status code
app.get('/error', (req, res) => {
  res.status(500).render('error', {
    message: 'Internal Server Error',
    error: process.env.NODE_ENV === 'development' ? err : {}
  })
})

// Conditional rendering based on content type
app.get('/users/:id', async (req, res) => {
  const user = await findUser(req.params.id)
  if (!user) {
    return res.status(404).render('404', { resource: 'User' })
  }

  // Content negotiation
  res.format({
    html: () => res.render('user', { user }),
    json: () => res.json(user),
    default: () => res.status(406).send('Not Acceptable')
  })
})

// Send file directly
app.get('/download/:file', (req, res) => {
  const filePath = path.join(__dirname, 'files', req.params.file)
  res.download(filePath, (err) => {
    if (err) res.status(404).json({ error: 'File not found' })
  })
})

app.listen(3000)
```
