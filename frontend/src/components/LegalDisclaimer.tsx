/**
 * Persistent informational-only disclaimer mounted at the bottom of
 * every authenticated page in the (app) layout.
 *
 * Why it exists: ClearScript's analyzers cite statutes by section
 * number and recommend specific contract changes, which sits close to
 * the line of "providing legal advice." Brad Gallagher's legal review
 * brief Question #1 is specifically about where this disclaimer needs
 * to appear and the answer is "everywhere a user can see analysis
 * output, not just in the exported PDF footer."
 *
 * Kept deliberately small and unobtrusive — bottom of the page, gray
 * text, no shadow, no card. The point is presence, not prominence.
 */
export default function LegalDisclaimer() {
  return (
    <div className="border-t border-gray-100 mt-2 pt-4 pb-6">
      <p className="text-[11px] text-gray-400 leading-relaxed max-w-3xl">
        ClearScript provides informational analysis only. It is not a law firm
        and does not provide legal advice. The deal scores, redline suggestions,
        compliance flags, and dollar-denominated leakage estimates produced by
        the platform are intended to help benefits leaders prepare for
        conversations with qualified ERISA counsel — not to substitute for one.
        Consult your attorney before relying on any output for negotiation,
        compliance, audit, or enforcement decisions.
      </p>
    </div>
  );
}
