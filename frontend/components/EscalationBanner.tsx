export default function EscalationBanner() {
  return (
    <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 text-sm px-4 py-3 rounded-lg mx-4 mb-2 flex items-center gap-2">
      <span>🔔</span>
      <span>
        This query has been escalated to a <strong>human agent</strong>. You
        will be contacted shortly.
      </span>
    </div>
  );
}