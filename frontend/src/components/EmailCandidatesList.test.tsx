import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EmailCandidatesList } from './EmailCandidatesList'

describe('EmailCandidatesList', () => {
  it('shows its empty state', () => {
    render(<EmailCandidatesList candidates={[]} />)
    expect(screen.getByText('No email candidates')).toBeInTheDocument()
  })

  it('marks the primary candidate', () => {
    render(
      <EmailCandidatesList
        candidates={[
          {
            id: 'candidate-1',
            person_id: 'person-1',
            email: 'lead@example.com',
            source: 'manual',
            status: 'verified',
            confidence: 1,
            is_primary: true,
            created_at: '2026-10-07T00:00:00Z',
          },
        ]}
      />,
    )
    expect(screen.getByText('PRIMARY')).toBeInTheDocument()
  })
})
