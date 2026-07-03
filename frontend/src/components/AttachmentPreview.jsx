const KIND_LABEL = { image: "Image" };

export default function AttachmentPreview({ attachment, onRemove }) {
  const { original_filename, kind, extraction_status, extraction_error, extracted_text } =
    attachment;

  return (
    <div className={`attachment-preview attachment-${extraction_status}`}>
      <div className="attachment-header">
        <span className="attachment-kind">{KIND_LABEL[kind] || kind}</span>
        <span className="attachment-filename">{original_filename}</span>
        {onRemove && (
          <button type="button" className="attachment-remove" onClick={onRemove}>
            ×
          </button>
        )}
      </div>
      {extraction_status === "pending" && <div className="attachment-status">Extracting…</div>}
      {extraction_status === "failed" && (
        <div className="attachment-status attachment-error">{extraction_error}</div>
      )}
      {extraction_status === "success" && extracted_text && (
        <details className="attachment-extracted">
          <summary>Extracted content</summary>
          <pre>{extracted_text}</pre>
        </details>
      )}
    </div>
  );
}
