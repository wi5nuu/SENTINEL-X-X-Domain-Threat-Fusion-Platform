module.exports = {
  networks: {
    hardhat: {
      chainId: 31337,
      loggingEnabled: false,
    },
  },
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  paths: {
    sources: "./contracts",
    artifacts: "./artifacts",
  },
};
