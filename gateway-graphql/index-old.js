import { ApolloServer, gql } from 'apollo-server';
import fetch from 'node-fetch';

const typeDefs = gql`
  type Product {
    id: ID!
    name: String!
    price: Float!
    stock: Int!
    category: String
    description: String
    lowStock: Boolean!
  }

  type Query {
    product(id: ID!): Product
    products(limit: Int, category: String): [Product!]!
    recommendations(id: ID!, limit: Int = 3): [Product!]!
  }
`;

const REST_BASE = process.env.REST_BASE_URL || "http://localhost:8080";
const LOW_STOCK_THRESHOLD = parseInt(process.env.LOW_STOCK_THRESHOLD || "10", 10);

const resolvers = {
  Product: {
    lowStock: (parent) => parent.stock <= LOW_STOCK_THRESHOLD,
  },
  Query: {
    product: async (_, { id }) => {
      const res = await fetch(`${REST_BASE}/products/${id}`);
      if (res.status !== 200) return null;
      return res.json();
    },
    products: async (_, { limit, category }) => {
      const qs = new URLSearchParams();
      if (limit) qs.append("limit", limit);
      if (category) qs.append("category", category);
      const res = await fetch(`${REST_BASE}/products${qs.toString() ? "?" + qs.toString() : ""}`);
      return res.json();
    },
    recommendations: async (_, { id, limit }) => {
      const res = await fetch(`${REST_BASE}/products/${id}/recommendations?limit=${limit}`);
      if (res.status !== 200) return [];
      return res.json();
    },
  },
};

const server = new ApolloServer({
  typeDefs,
  resolvers,
  plugins: [], // disabilita tracing extra
});

server.listen({ port: 4000 }).then(({ url }) => console.log(`GraphQL ready at ${url}`));