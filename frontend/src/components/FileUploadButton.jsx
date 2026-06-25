import { useRef } from "react";

const ACCEPTED = ".jpg,.jpeg,.png,.webp,.csv,.xlsx";

export default function FileUploadButton({ onSelect, disabled }) {
  const inputRef = useRef(null);

  function handleChange(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onSelect(file);
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        style={{ display: "none" }}
        onChange={handleChange}
      />
      <button
        type="button"
        className="upload-button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        title="Attach image, CSV, or XLSX"
      >
        📎
      </button>
    </>
  );
}
