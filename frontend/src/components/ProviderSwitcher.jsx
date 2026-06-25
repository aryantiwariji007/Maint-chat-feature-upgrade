export default function ProviderSwitcher({ provider, onChange, disabled }) {
  return (
    <select
      className="provider-switcher"
      value={provider}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="gemini">Gemini</option>
      <option value="anthropic">Anthropic</option>
    </select>
  );
}
