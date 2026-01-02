import { ApolloServer, gql } from 'apollo-server';
import fetch from 'node-fetch';

const typeDefs = gql`
  type Product { id: ID!, name: String!, price: Float!, stock: Int!, lowStock: Boolean! }
  type Query {
    products: [Product!]!
    product(id: ID!): Product
    recommendations(id: ID!): [Product!]!
  }
`;

const REST_BASE = process.env.REST_BASE_URL || "http://localhost:8080";

const resolvers = {
  Product: {
    lowStock: (parent) => parent.stock <= 10, // soglia demo
  },
  Query: {
    products: async () => {
      const res = await fetch(`${REST_BASE}/products`);
      return res.json();
    },
    product: async (_, { id }) => {
      const res = await fetch(`${REST_BASE}/products/${id}`);
      if (res.status !== 200) return null;
      return res.json();
    },
    recommendations: async (_, { id }) => {
      const res = await fetch(`${REST_BASE}/products`);
      const items = await res.json();
      return items.filter(p => String(p.id) !== String(id)).slice(0, 3);
    }
  }
};

const server = new ApolloServer({ typeDefs, resolvers });
server.listen({ port: 4000 }).then(({ url }) => console.log(`GraphQL ready at ${url}`));