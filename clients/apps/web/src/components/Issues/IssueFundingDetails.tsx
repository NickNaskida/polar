import { schemas } from '@polar-sh/client'
import FundingPill from './FundingPill'
import PledgeSummaryPill from './PledgeSummaryPill'
import PublicRewardPill from './PublicRewardPill'

interface IssueFundingDetailsProps {
  organization: schemas['Organization']
  issue: schemas['Issue']
  total: schemas['CurrencyAmount']
  fundingGoal: schemas['CurrencyAmount'] | null
  pledgesSummaries: schemas['PledgesTypeSummaries']
  showLogo?: boolean
  showStatus?: boolean
  summaryRight?: React.ReactElement
}

const IssueFundingDetails: React.FC<IssueFundingDetailsProps> = ({
  organization,
  issue,
  total,
  fundingGoal,
  pledgesSummaries,
}) => {
  const { pay_upfront, pay_on_completion } = pledgesSummaries

  const upfrontSplit =
    issue.upfront_split_to_contributors ??
    organization.default_upfront_split_to_contributors

  return (
    <div className="flex flex-col items-center gap-4 md:flex-row">
      <FundingPill total={total} goal={fundingGoal} />

      <div className="flex flex-row items-center gap-4">
        {pay_upfront.total.amount > 0 && (
          <PledgeSummaryPill.Funded summary={pay_upfront} />
        )}

        {pay_on_completion.total.amount > 0 && (
          <PledgeSummaryPill.Pledged summary={pay_on_completion} />
        )}
      </div>

      {upfrontSplit ? <PublicRewardPill percent={upfrontSplit} /> : null}
    </div>
  )
}

export default IssueFundingDetails
