'use client'

import { parseGitHubIssueLink } from '@/utils/github'
import { useRouter } from 'next/navigation'

import Button from '@polar-sh/ui/components/atoms/Button'
import Input from '@polar-sh/ui/components/atoms/Input'
import { ChangeEvent, MouseEvent, useState } from 'react'
import WhiteCard from '../Cards/WhiteCard'
import HowItWorks from './HowItWorks'

const PledgeByLink = ({
  initLinkValue,
  initErrorMessage,
}: {
  initLinkValue: string
  initErrorMessage: string
}) => {
  const router = useRouter()
  const [errorMessage, setErrorMessage] = useState(initErrorMessage)
  const [link, setLink] = useState(initLinkValue)

  const onLinkChange = async (event: ChangeEvent<HTMLInputElement>) => {
    setErrorMessage('')
    setLink(event.target.value)
  }

  const pledgeToIssue = async (event: MouseEvent) => {
    event.preventDefault()

    const issue = parseGitHubIssueLink(link)

    if (!issue) {
      setErrorMessage('Invalid GitHub issue link')
      return
    }

    // If on polar.new, make sure to redirect user to polar.sh
    router.push(
      `https://polar.sh/${issue.owner}/${issue.repo}/issues/${issue.number}`,
    )
  }

  return (
    <>
      <div className="mx-auto mt-12 w-full p-6 md:mt-24 md:w-[826px]">
        <h1 className="text-center text-3xl font-normal text-gray-800 md:text-4xl dark:text-white">
          Back an issue
        </h1>

        <div className="mb-12 mt-8 flex flex-col md:mt-14">
          <WhiteCard
            className="flex flex-col items-stretch rounded-none p-2 text-center md:flex-row md:rounded-xl md:pr-0"
            padding={false}
          >
            <div className="w-full px-3 py-5 text-left md:px-6">
              <form className="flex flex-col">
                <label
                  htmlFor="link"
                  className="text mb-2 mt-4 text-sm font-medium"
                >
                  GitHub issue link{' '}
                  <span className="dark:text-polar-400 font-normal text-gray-500">
                    (e.g. https://github.com/
                    <wbr />
                    polarsource/
                    <wbr />
                    polar/
                    <wbr />
                    issues/
                    <wbr />
                    123, polarsource/polar#123)
                  </span>
                </label>

                <Input
                  id="link"
                  onChange={onLinkChange}
                  onBlur={onLinkChange}
                  value={link}
                />

                <div className="mt-6">
                  <Button onClick={pledgeToIssue}>Pledge</Button>
                </div>

                {errorMessage && (
                  <p className="mt-2 text-sm text-red-500">{errorMessage}</p>
                )}
              </form>
            </div>
          </WhiteCard>
        </div>

        <HowItWorks />
      </div>
    </>
  )
}

export default PledgeByLink
