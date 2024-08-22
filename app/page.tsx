import { Label } from "./components/label";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <p>Just a paragraph</p>

      <div>
        <Label status="pending" />
        <Label status="paid" />
      </div>
    </main>
  );
}
