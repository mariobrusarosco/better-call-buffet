import clsx from "clsx";

export const Label = ({ status }: { status: "pending" | "paid" }) => {
  return (
    <span
      className={clsx("flex gap-4 rounded-md text-white p-5", {
        "bg-red-800": status === "pending",
        "bg-green-800": status === "paid",
      })}
    >
      label
    </span>
  );
};
