// 詳細ページ：URL の id（例：/items/3 の 3）を取り出して、画面の部品に渡す
import ItemDetail from "./ItemDetail";

export default async function ItemPage({ params }: PageProps<"/items/[id]">) {
  const { id } = await params;
  return <ItemDetail id={id} />;
}
