import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ArticlesList } from './ArticlesPage'

describe('ArticlesList', () => {
  it('shows an empty state', () => {
    render(
      <MemoryRouter>
        <ArticlesList articles={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByText('No articles yet.')).toBeInTheDocument()
  })
})
