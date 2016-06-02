import unittest
import train
import pandas as pd

class TestTrain(unittest.TestCase):

    def test_num_away(self):
        red_line_B11 = pd.read_pickle("RD_B11.pkl")
        train_df = pd.read_pickle("test.pkl")
        train_df1 = pd.read_pickle("test1.pkl")
        # test when they are the same
        t = train_df.iloc[0].LocationCode
        t1 = train_df1.iloc[0].LocationCode
        n = train.num_away(t, t1, red_line_B11)
        self.assertEqual(n, 0)
        # test when different
        t = train_df.iloc[8].LocationCode
        t1 = train_df1.iloc[0].LocationCode
        n = train.num_away(t, t1, red_line_B11)
        self.assertEqual(n, 12)
        # test that switching the order switches the sign
        n = train.num_away(t1, t, red_line_B11)
        self.assertEqual(n, -12)


    def test_distance(self):
        red_line_B11 = pd.read_pickle("RD_B11.pkl")
        train_df = pd.read_pickle("test.pkl")
        train_df1 = pd.read_pickle("test1.pkl")
        distance = train.train_distance(train_df.iloc[0], train_df1.iloc[0], red_line_B11)
        self.assertEqual(distance, 0)
        distance = train.train_distance(train_df.iloc[0], train_df1.iloc[1], red_line_B11)
        self.assertGreater(distance, 0)


if __name__ == '__main__':
    unittest.main()
