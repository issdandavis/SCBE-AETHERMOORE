# React
> Source: Context7 MCP | Category: code
> Fetched: 2026-04-04

### State: a component's memory

Source: https://react.dev/learn/adding-interactivity

You can add state to a component with a `useState` Hook. Hooks are special functions that let your components use React features (state is one of those features). The `useState` Hook lets you declare a state variable. It takes the initial state and returns a pair of values: the current state, and a state setter function that lets you update it.

---

### useState Hook — Multiple State Variables

Source: https://react.dev/blog/2023/03/16/introducing-react-dev

Manage multiple independent state variables in the same component using the useState hook. Each state variable is completely independent.

```javascript
import { useState } from 'react';

export default function Form() {
  const [name, setName] = useState('Taylor');
  const [age, setAge] = useState(42);

  return (
    <>
      <input
        value={name}
        onChange={e => setName(e.target.value)}
      />
      <button onClick={() => setAge(age + 1)}>
        Increment age
      </button>
      <p>Hello, {name}. You are {age}.</p>
    </>
  );
}
```

---

### Manage Multiple State Variables in a React Component

Source: https://react.dev/learn/state-a-components-memory

Demonstrates how to use multiple `useState` hooks to manage independent state variables within a single functional component — a gallery component that uses an `index` for navigation and a `showMore` boolean to toggle details.

```javascript
import { useState } from 'react';
import { sculptureList } from './data.js';

export default function Gallery() {
  const [index, setIndex] = useState(0);
  const [showMore, setShowMore] = useState(false);

  function handleNextClick() {
    setIndex(index + 1);
  }

  function handleMoreClick() {
    setShowMore(!showMore);
  }

  let sculpture = sculptureList[index];
  return (
    <>
      <button onClick={handleNextClick}>
        Next
      </button>
      <h2>
        <i>{sculpture.name} </i>
        by {sculpture.artist}
      </h2>
      <h3>
        ({index + 1} of {sculptureList.length})
      </h3>
      <button onClick={handleMoreClick}>
        {showMore ? 'Hide' : 'Show'} details
      </button>
      {showMore && <p>{sculpture.description}</p>}
      <img
        src={sculpture.url}
        alt={sculpture.alt}
      />
    </>
  );
}
```

---

### State Management and Event Handling Component

Source: https://react.dev/learn/understanding-your-ui-as-a-tree

The InspirationGenerator component demonstrates React state management using useState hook, event handling with onClick, and rendering child components through props.children.

```javascript
import * as React from 'react';
import quotes from './quotes';
import FancyText from './FancyText';

export default function InspirationGenerator({children}) {
  const [index, setIndex] = React.useState(0);
  const quote = quotes[index];
  const next = () => setIndex((index + 1) % quotes.length);

  return (
    <>
      <p>Your inspirational quote is:</p>
      <FancyText text={quote} />
      <button onClick={next}>Inspire me again</button>
      {children}
    </>
  );
}
```
