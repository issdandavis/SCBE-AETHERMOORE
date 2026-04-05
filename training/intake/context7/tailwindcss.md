# Tailwind CSS
> Source: Context7 MCP | Category: code
> Fetched: 2026-04-04

### Grid Template Columns Utility Classes

Source: https://github.com/tailwindlabs/tailwindcss.com/blob/main/src/docs/grid-template-columns.mdx

Tailwind CSS utility class definitions for grid-template-columns. Provides predefined classes for common grid configurations (numbered columns, none, subgrid), arbitrary values in brackets, and custom CSS properties.

```css
grid-cols-<number> {
  grid-template-columns: repeat(<number>, minmax(0, 1fr));
}

grid-cols-none {
  grid-template-columns: none;
}

grid-cols-subgrid {
  grid-template-columns: subgrid;
}

grid-cols-[<value>] {
  grid-template-columns: <value>;
}

grid-cols-(<custom-property>) {
  grid-template-columns: var(<custom-property>);
}
```

---

### Utility-First Approach

Source: https://github.com/tailwindlabs/tailwindcss.com/blob/main/src/docs/styling-with-utility-classes.mdx

Tailwind CSS uses a utility-first approach where you style elements by combining many single-purpose presentational classes, known as utility classes, directly in your markup. Rather than writing custom CSS, you apply pre-defined utility classes to HTML elements to achieve your desired styling.

```html
<div class="flex items-center space-x-2 text-base">
  <h4 class="font-semibold text-slate-900">Contributors</h4>
  <span class="bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">204</span>
</div>
<div class="mt-3 flex -space-x-2 overflow-hidden">
  <img class="inline-block h-12 w-12 rounded-full ring-2 ring-white"
       src="https://images.unsplash.com/photo-1491528323818-fdd1faba62cc?auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
       alt="" />
  <img class="inline-block h-12 w-12 rounded-full ring-2 ring-white"
       src="https://images.unsplash.com/photo-1550525811-e5869dd03032?auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
       alt="" />
</div>
```

---

### Tailwind CSS v4 Introduction

Source: https://context7.com/tailwindlabs/tailwindcss.com/llms.txt

Tailwind CSS v4 is a utility-first CSS framework that provides low-level utility classes for building custom designs directly in your HTML. Unlike traditional CSS frameworks that offer pre-designed components, Tailwind gives you atomic CSS classes like `flex`, `pt-4`, `text-center`, and `rotate-90` that can be composed to build any design. The framework is configured entirely through CSS using the `@theme` directive, eliminating the need for JavaScript configuration files and enabling a more native CSS development experience.

---

### Managing Duplication

Source: https://github.com/tailwindlabs/tailwindcss.com/blob/main/src/docs/styling-with-utility-classes.mdx

When you build entire projects with just utility classes, you'll inevitably find yourself repeating certain patterns to recreate the same design in different places. This duplication occurs naturally as you apply the same visual styles across multiple components and elements throughout your project. However, this is a common and manageable aspect of utility-first CSS development that has established solutions.
