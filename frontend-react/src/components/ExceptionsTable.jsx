export default function ExceptionsTable({ rows, columns, emptyLabel }) {
  if (!rows) {
    return <p className="empty-note">Run this step to pull the latest records.</p>;
  }
  if (rows.length === 0) {
    return <p className="empty-note empty-note--clear">{emptyLabel}</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.record_ref ? `${row.record_ref}-${i}` : i}>
              {columns.map((col) => (
                <td key={col.key}>{row[col.key] ?? "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
