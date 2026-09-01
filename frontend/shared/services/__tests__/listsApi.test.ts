import { describe, it, expect, vi, beforeEach } from "vitest";

// `listsApi` passe par l'instance axios partagée (`./api`), pas par le module
// `axios` global : c'est cette instance qu'il faut mocker.
vi.mock("../api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const { default: api } = await import("../api");
const { listsApi, ListsApiError } = await import("../listsApi");

const mockedApi = vi.mocked(api);

const mockLists = [
  {
    id: 1,
    name: "A faire",
    order: 1,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "En cours",
    order: 2,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: 3,
    name: "Terminé",
    order: 3,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

/** Erreur axios telle que la voit `handleApiError`. */
const httpError = (status: number, detail?: string) => ({
  response: { status, data: detail === undefined ? {} : { detail } },
});

describe("listsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // `getLists` met ses résultats en cache : sans ça, un test pollue le suivant.
    listsApi.invalidateCache();
  });

  describe("getLists", () => {
    it("fetches lists successfully", async () => {
      mockedApi.get.mockResolvedValue({ data: mockLists });

      const result = await listsApi.getLists();

      expect(mockedApi.get).toHaveBeenCalledWith("/lists/");
      expect(result).toEqual(mockLists);
    });

    it("sorts lists by order", async () => {
      mockedApi.get.mockResolvedValue({
        data: [mockLists[2], mockLists[0], mockLists[1]],
      });

      const result = await listsApi.getLists();

      expect(result.map((l) => l.order)).toEqual([1, 2, 3]);
    });

    it("handles API error", async () => {
      mockedApi.get.mockRejectedValue(new Error("Network Error"));

      await expect(listsApi.getLists()).rejects.toBeInstanceOf(ListsApiError);
      expect(mockedApi.get).toHaveBeenCalledWith("/lists/");
    });

    it("returns empty array when no lists exist", async () => {
      mockedApi.get.mockResolvedValue({ data: [] });

      await expect(listsApi.getLists()).resolves.toEqual([]);
    });
  });

  describe("cache", () => {
    it("serves the second call from cache", async () => {
      mockedApi.get.mockResolvedValue({ data: mockLists });

      await listsApi.getLists();
      const cached = await listsApi.getLists();

      expect(mockedApi.get).toHaveBeenCalledTimes(1);
      expect(cached).toEqual(mockLists);
    });

    it("refetches when the cache is invalidated", async () => {
      mockedApi.get.mockResolvedValue({ data: mockLists });

      await listsApi.getLists();
      listsApi.invalidateCache();
      await listsApi.getLists();

      expect(mockedApi.get).toHaveBeenCalledTimes(2);
    });

    it("refetches when useCache is false", async () => {
      mockedApi.get.mockResolvedValue({ data: mockLists });

      await listsApi.getLists();
      await listsApi.getLists(false);

      expect(mockedApi.get).toHaveBeenCalledTimes(2);
    });
  });

  describe("createList", () => {
    it("creates a list successfully", async () => {
      const newListData = { name: "New List", order: 4 };
      const createdList = {
        id: 4,
        ...newListData,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };
      mockedApi.post.mockResolvedValue({ data: createdList });

      const result = await listsApi.createList(newListData);

      expect(mockedApi.post).toHaveBeenCalledWith("/lists/", newListData);
      expect(result).toEqual(createdList);
    });

    it("handles validation errors", async () => {
      mockedApi.post.mockRejectedValue(httpError(422, "Validation error"));

      await expect(
        listsApi.createList({ name: "", order: 0 }),
      ).rejects.toMatchObject({
        name: "ApiError",
        status: 422,
        code: "UNPROCESSABLE_ENTITY",
        message: "Validation error",
      });
    });

    it("handles duplicate name errors", async () => {
      const detail = 'Une liste avec le nom "A faire" existe déjà';
      mockedApi.post.mockRejectedValue(httpError(400, detail));

      await expect(
        listsApi.createList({ name: "A faire", order: 4 }),
      ).rejects.toMatchObject({
        status: 400,
        code: "VALIDATION_ERROR",
        message: detail,
      });
    });
  });

  describe("updateList", () => {
    it("updates a list successfully", async () => {
      const updateData = { name: "Updated Name" };
      const updatedList = {
        ...mockLists[0],
        ...updateData,
        updated_at: "2024-01-02T00:00:00Z",
      };
      mockedApi.put.mockResolvedValue({ data: updatedList });

      const result = await listsApi.updateList(1, updateData);

      expect(mockedApi.put).toHaveBeenCalledWith("/lists/1", updateData);
      expect(result).toEqual(updatedList);
    });

    it("handles list not found error", async () => {
      mockedApi.put.mockRejectedValue(httpError(404, "Liste non trouvée"));

      await expect(
        listsApi.updateList(999, { name: "Updated Name" }),
      ).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
        message: "Liste non trouvée",
      });
    });

    it("handles duplicate name on update", async () => {
      const detail = 'Une liste avec le nom "En cours" existe déjà';
      mockedApi.put.mockRejectedValue(httpError(400, detail));

      await expect(
        listsApi.updateList(1, { name: "En cours" }),
      ).rejects.toMatchObject({ status: 400, message: detail });
    });

    it("updates only provided fields", async () => {
      const updatedList = {
        ...mockLists[0],
        order: 5,
        updated_at: "2024-01-02T00:00:00Z",
      };
      mockedApi.put.mockResolvedValue({ data: updatedList });

      const result = await listsApi.updateList(1, { order: 5 });

      expect(mockedApi.put).toHaveBeenCalledWith("/lists/1", { order: 5 });
      expect(result.order).toBe(5);
      expect(result.name).toBe(mockLists[0].name);
    });
  });

  describe("deleteList", () => {
    it("deletes a list successfully", async () => {
      mockedApi.delete.mockResolvedValue({
        data: { message: "Liste supprimée avec succès" },
      });

      await listsApi.deleteList(2, 1);

      expect(mockedApi.delete).toHaveBeenCalledWith("/lists/2", {
        data: { target_list_id: 1 },
      });
    });

    it("handles last list deletion error", async () => {
      const detail = "Impossible de supprimer la dernière liste";
      mockedApi.delete.mockRejectedValue(httpError(400, detail));

      await expect(listsApi.deleteList(1, 1)).rejects.toMatchObject({
        status: 400,
        message: detail,
      });
    });

    it("handles list not found error", async () => {
      mockedApi.delete.mockRejectedValue(httpError(404, "Liste non trouvée"));

      await expect(listsApi.deleteList(999, 1)).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
      });
    });

    it("handles invalid target list error", async () => {
      const detail = "La liste de destination n'existe pas";
      mockedApi.delete.mockRejectedValue(httpError(400, detail));

      await expect(listsApi.deleteList(2, 999)).rejects.toMatchObject({
        status: 400,
        message: detail,
      });
    });
  });

  describe("reorderLists", () => {
    it("reorders lists successfully", async () => {
      const listOrders = { 1: 3, 2: 1, 3: 2 };
      mockedApi.post.mockResolvedValue({
        data: { message: "Listes réorganisées avec succès" },
      });

      await listsApi.reorderLists(listOrders);

      expect(mockedApi.post).toHaveBeenCalledWith("/lists/reorder", {
        list_orders: listOrders,
      });
    });

    it("invalidates the cache after reordering", async () => {
      mockedApi.get.mockResolvedValue({ data: mockLists });
      mockedApi.post.mockResolvedValue({ data: {} });

      await listsApi.getLists();
      await listsApi.reorderLists({ 1: 2, 2: 1 });
      await listsApi.getLists();

      expect(mockedApi.get).toHaveBeenCalledTimes(2);
    });

    it("handles invalid order data", async () => {
      const detail = "Tous les ordres doivent être positifs";
      mockedApi.post.mockRejectedValue(httpError(422, detail));

      await expect(
        listsApi.reorderLists({ 1: -1, 2: 0 }),
      ).rejects.toMatchObject({ status: 422, message: detail });
    });

    it("handles duplicate orders", async () => {
      const detail = "Les ordres doivent être uniques";
      mockedApi.post.mockRejectedValue(httpError(422, detail));

      await expect(listsApi.reorderLists({ 1: 1, 2: 1 })).rejects.toMatchObject(
        { status: 422, message: detail },
      );
    });

    it("handles non-existing lists in reorder", async () => {
      const detail = "Les listes suivantes n'existent pas: {999}";
      mockedApi.post.mockRejectedValue(httpError(400, detail));

      await expect(
        listsApi.reorderLists({ 1: 1, 999: 2 }),
      ).rejects.toMatchObject({ status: 400, message: detail });
    });
  });

  describe("getListCardsCount", () => {
    it("gets card count for a list successfully", async () => {
      mockedApi.get.mockResolvedValue({
        data: { list_id: 1, list_name: "A faire", cards_count: 5 },
      });

      const result = await listsApi.getListCardsCount(1);

      expect(mockedApi.get).toHaveBeenCalledWith("/lists/1/cards-count");
      expect(result.list.id).toBe(1);
      expect(result.list.name).toBe("A faire");
      expect(result.card_count).toBe(5);
    });

    it("handles list not found for card count", async () => {
      mockedApi.get.mockRejectedValue(httpError(404, "Liste non trouvée"));

      await expect(listsApi.getListCardsCount(999)).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
      });
    });

    it("returns zero count for empty list", async () => {
      mockedApi.get.mockResolvedValue({
        data: { list_id: 3, list_name: "Terminé", cards_count: 0 },
      });

      const result = await listsApi.getListCardsCount(3);

      expect(result.card_count).toBe(0);
    });
  });

  describe("error handling", () => {
    it("maps network errors (no response) to NETWORK_ERROR", async () => {
      mockedApi.get.mockRejectedValue(new Error("Network Error"));

      await expect(listsApi.getLists()).rejects.toMatchObject({
        status: 0,
        code: "NETWORK_ERROR",
      });
    });

    it("maps server errors to INTERNAL_SERVER_ERROR", async () => {
      mockedApi.get.mockRejectedValue(httpError(500, "Internal Server Error"));

      await expect(listsApi.getLists()).rejects.toMatchObject({
        status: 500,
        code: "INTERNAL_SERVER_ERROR",
      });
    });

    it("maps authentication errors to UNAUTHORIZED", async () => {
      mockedApi.get.mockRejectedValue(httpError(401, "Not authenticated"));

      await expect(listsApi.getLists()).rejects.toMatchObject({
        status: 401,
        code: "UNAUTHORIZED",
      });
    });

    it("maps authorization errors to FORBIDDEN", async () => {
      mockedApi.post.mockRejectedValue(
        httpError(403, "Not enough permissions"),
      );

      await expect(
        listsApi.createList({ name: "Test", order: 1 }),
      ).rejects.toMatchObject({ status: 403, code: "FORBIDDEN" });
    });
  });

  describe("request configuration", () => {
    it("sends requests to the expected endpoint", async () => {
      mockedApi.get.mockResolvedValue({ data: mockLists });

      await listsApi.getLists();

      expect(mockedApi.get).toHaveBeenCalledWith("/lists/");
    });

    it("maps request timeouts to NETWORK_ERROR", async () => {
      mockedApi.get.mockRejectedValue(new Error("timeout of 5000ms exceeded"));

      await expect(listsApi.getLists()).rejects.toMatchObject({
        code: "NETWORK_ERROR",
      });
    });
  });
});
